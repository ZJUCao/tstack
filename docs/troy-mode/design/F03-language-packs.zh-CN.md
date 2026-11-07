# F03 设计：语言包

> 本文件是 [`F03-language-packs.md`](F03-language-packs.md) 的中文镜像，同步自英文版 1.2（2026-11-07）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 功能 | [需求文档 1.6](../requirements.zh-CN.md#72-功能列表) 中的 F03 |
| 版本 | 1.2 |
| 日期 | 2026-11-07 |
| 状态 | Troy 已于 2026-11-05 批准，含 D15 到 D24。1.1 版加入 Troy 于 2026-11-06 决定的 D25 和 D26。1.2 版记录 F06 已批准设计带来的修改（D49、D50）。 |
| 事实来源 | 英文版 [`F03-language-packs.md`](F03-language-packs.md)。本文件是中文镜像。 |

## 1. 范围

F03 让 troy-check 执行与项目语言相关的规则：

| 规则 | F03 检查什么 | 适用范围 |
| --- | --- | --- |
| R04 | 函数体最多 50 行代码。 | 改动的函数 |
| R05 | 每个函数和类都有 Google 风格的文档注释。注释和文档注释里没有中文、日文或韩文。 | 改动的函数和改动的行 |
| R06 | 源码文件最多 500 行（软限制）。 | 改动的源码文件 |
| R07 | 模块之间只按允许的方向依赖，只通过对外接口依赖，且不能成环。 | 改动文件里的导入 |
| R09 | 测试 PR 里的每个新测试，在 mock 上都失败。 | 本 PR 所属功能或 bug 的测试 |
| R10 | 每个测试都带有它的用例编号或 bug 编号。只有尚未验收的功能和尚未修复的 bug 的测试允许失败。 | 所有测试 |
| R11 | 改动的代码行覆盖率至少 90%，分支覆盖率至少 80%。 | `impl` 和 `fix` PR 里改动的行 |

需求文档里 R09 不属于任何功能。F02 设计把它留给了 F03，所以由 F03 负责（D15）。

按照 Q6，R04 到 R07 和 R11 只看新增和改动的代码。旧代码在被改动时再整改。

F03 分两部分（D15）：

1. **引擎。** troy-check 里与语言无关的代码，只用标准库。它以 JUnit XML 读取测试结果，以 Cobertura XML 读取覆盖率，并通过每种语言一个的小适配器读取源码。几乎所有测试运行器和覆盖率工具都能输出这两种格式。
2. **语言包。** 先做 Python，再做 C/C++。每个语言包包括：环境、工具配置、构建和测试命令、CI 任务、给 F02 配置用的路径规则，以及适配器。

以后的 TypeScript/JavaScript 语言包可以沿用同样的结构，本设计不涉及。

## 2. 位置

```text
troy-mode/
  checks/
    troycheck/          F02's modules plus the engine (internal modules: the Developer's choice)
  lang/
    python/
      README.md         README.zh-CN.md
      environment.yml   pyproject.toml (fragment)   config.toml (fragment)   workflow-job.yml
      pyproject-project.toml   (the start of a new project's pyproject.toml, F06)
    cpp/
      README.md         README.zh-CN.md
      environment.yml   requirements-tools.in   CMakePresets.json   cmake/troy.cmake   Doxyfile
      .clang-format     .clang-tidy         config.toml (fragment)   workflow-job.yml
      include/troy/not_implemented.h   (the exception that mock bodies throw)
      CMakeLists-project.txt   (a new project's CMakeLists.txt, F06)
  samples/
    python/  cpp/      sample projects that troy-pstack's CI takes through each pack (section 10)
  dev/
    build_sample.py    builds a sample's git repository, through troy-init's own functions (F06)
    environment.yml    requirements-dev.lock   troy-pstack's own environment (D26)
```

每个语言包的 README 列出它的文件、这些文件在项目里放在哪里，以及第 8.3 节和第 9.4 节的命令。`troy-init`（F06）负责把选定的语言包复制进项目。

## 3. 命令行接口：`troy-check code`

```text
python .troy-mode/checks/troy_check.py code --base <ref> [--head <ref>] --title <text> [--body-file <path>] [--junit <path>]... [--coverage <path>]... [--doc-warnings <path>] [--repo <path>] [--json]
```

| 选项 | 含义 |
| --- | --- |
| `--base`、`--head`、`--title`、`--body-file`、`--repo`、`--json` | 同 `pr`（F02 设计第 3.1 节）。 |
| `--junit` | 测试运行输出的 JUnit XML 文件，可以给多个。不提供时，R09 和 R10 为 `skip`。 |
| `--coverage` | 覆盖率工具输出的 Cobertura XML 文件，可以给多个。不提供时，R11 为 `skip`。 |
| `--doc-warnings` | 仅用于 C/C++：Doxygen 的警告日志，供 R05 使用（第 9.3 节）。 |

报告格式和退出码同 F02 设计第 3.3 节。结果按 R04、R05、R06、R07、R09、R10、R11 的顺序给出。CI 总会传 `--junit` 和 `--coverage`，所以 CI 里出现 `skip` 说明工作流坏了，而不是规则通过了。

`.troy-mode/config.toml` 里的 `[lang] name` 选择适配器：`"python"` 或 `"cpp"`。和其他配置一样，它从合并基点那个 commit 读取。

C/C++ 适配器需要 lizard（第 6 节），所以在 C/C++ 项目里，`troy-check code` 要用项目环境里的 Python 运行。Python 适配器只用标准库。

F03 还修改 F02 的 `pr` 子命令：R01 还要检查 commit 的标题行等于 PR 标题（D17）。

## 4. 测试名称和测试策略（R09、R10）

### 4.1 标记（D16）

测试自己的名字以测试方案里的用例编号开头，或者以 bug 编号开头。troy-check 从 JUnit XML 读取测试名称，所以这种标记方式在每种语言里都一样。

| 语言 | 功能测试 | bug 测试 |
| --- | --- | --- |
| Python（pytest） | `def test_f04_t07_writes_header():` | `def test_b12_empty_history_does_not_crash():` |
| C++（GoogleTest） | `TEST(ExportCsv, F04_T07_WritesHeader)` | `TEST(History, B12_EmptyHistoryDoesNotCrash)` |

- 测试自己的名字，是 JUnit 里的测试名去掉 `test_` 前缀、去掉方括号里的参数后缀；对 GoogleTest，还要去掉测试套件名。
- 匹配时不分大小写，`-` 和 `_` 视为相同，所以 `f04_t07`、`F04_T07` 和 `F04-T07` 是同一个用例。
- 名字里没有编号的测试，R10 失败。例外是匹配 `[tests] legacy` 规则的文件，供带着已有测试接入 troy-mode 的项目使用（Q6）。
- R10 还会拿测试和该功能的测试方案 `docs/features/<feature-id>-<slug>/test-plan.md` 对照。方案里有用例却没有测试，或者测试对应的用例不在方案里，都给出 `warn`，交给测试经理处理。

### 4.2 哪些测试允许失败

已验收的功能和已修复的 bug，从合并基点那个 commit 的历史里读取（D17）：

- 标题行以 `[F04 6/6 accept]` 开头的 commit，表示 F04 已验收。
- 标题行以 `[B12 B/B fix]` 开头的 commit，表示 B12 已修复。

这之所以可行，是因为每个 PR 只有一个 commit（R01），而 F03 让 R01 还要求这个 commit 的标题行等于 PR 标题。rebase 合并会把这个标题行原样保留在 `main` 上。

| PR 类型 | 必须失败（R09） | 必须通过（R10） | 允许失败 |
| --- | --- | --- | --- |
| F04 的 `tests` | F04 的所有测试 | 已验收功能和已修复 bug 的测试 | 其他所有测试 |
| bug B12 的 `test` | B12 的所有测试 | 已验收功能和已修复 bug 的测试 | 其他所有测试 |
| F04 的 `impl` 或 `accept` | 无 | F04 的测试，加上上面那些 | 其他所有测试 |
| B12 的 `fix` | 无 | B12 的测试，加上上面那些 | 其他所有测试 |
| 其他任何类型 | 无 | 已验收功能和已修复 bug 的测试 | 其他所有测试 |

- JUnit 里的 failure 和 error 都算失败。被跳过的测试算作没有通过，所以跳过既藏不住必须通过的测试，也冒充不了必须失败的测试。
- 没有 JUnit 文件，或者 JUnit 文件报告了收集错误或构建错误，R10 失败。
- mock 的函数体只负责表明"尚未实现"（Python 里是 `raise NotImplementedError`，C++ 里是 `throw troy::NotImplemented{}`）。所以新接口的每个测试在 mock 上都会失败，正如 R09 要求的那样。

## 5. 覆盖率（R11）

- 适用于 `impl` 和 `fix` PR，其他类型跳过。
- 改动的行，是合并基点和 head 之间 `git diff -U0` 给出的、`source` 文件（F02 设计第 5 节）里新增或修改的行。
- 在 Cobertura XML 里，报告列出的改动行就是可执行行。行覆盖率 = 被覆盖的可执行改动行 ÷ 可执行改动行。分支覆盖率 = 改动行上被覆盖的分支走向 ÷ 改动行上的全部分支走向，从每行的 `condition-coverage` 读取。
- 阈值是 `[limits] line_coverage = 90` 和 `branch_coverage = 80`。没有可执行改动行的 PR 直接通过。
- 报告里的文件路径按它的 `<source>` 根目录解析，以便和仓库路径对上。
- 被排除的行，必须在同一行写明理由（D18），例如 `# pragma: no cover  reason: a full disk cannot be simulated` 或 `// GCOVR_EXCL_LINE reason: ...`。改动行上的排除注释没有 `reason:`，R11 失败。理由由测试经理在审查时批准。

## 6. 代码形态（R04、R05、R06）

每个适配器读取一个源码文件，返回其中的函数和类（名字、行范围、函数体行范围、是否带文档注释），以及其中的注释（行号和文字，包括文档注释）。

- **R04。** 对行范围碰到改动行的每个函数，统计函数体里含代码的行：不是空行、不是注释、也不是文档注释。超过 `[limits] function_lines = 50` 就失败。
- **R05。** 碰到改动行的每个函数和类都要有文档注释。文档注释的格式由该语言自己的工具检查（第 8.2 节和第 9.3 节）。改动行上的注释和文档注释不能含中文、日文或韩文字符（D23）。字符串字面量可以写任何文字。
- **R06。** 超过 `[limits] file_lines = 500` 行的改动源码文件：描述的"Soft-limit reason"一节给了理由就是 `warn`，没给就是 `fail`，和 R03 完全一样。

| 适配器部分 | Python | C/C++ |
| --- | --- | --- |
| 函数和类 | 标准库的 `ast` | lizard，一个能找出 C 和 C++ 函数及其行范围的 Python 包 |
| 注释 | `tokenize`，加上从 `ast` 取得的 docstring | troy-check 自己的 `//` 和 `/* */` 注释扫描器 |
| 文档注释 | docstring | 紧贴在声明上方的 `///` 或 `/** */` 注释块（D21） |

## 7. 模块依赖（R07）

模块映射来自 `docs/architecture.md` 第 3 节的表格，列为 Module、Owns、External interfaces 和 May depend on（D19）：

- **Owns** 和 **External interfaces** 列出用反引号括起来的路径规则，例如 `` `src/app/storage/**` `` 和 `` `src/app/storage/__init__.py` ``。
- **May depend on** 列出模块名，或者写"无"。

F01 架构模板第 3 节的填写说明随之修改，要求这样填。

导入关系按语言读取：

- **Python。** 用 `ast` 读取 `import` 和 `from ... import` 语句，并按 `[lang] source_roots`（例如 `["src"]`）解析到仓库里的文件。解析不到仓库文件的导入属于第三方，忽略。
- **C/C++。** `#include "..."` 行，相对于所在文件的文件夹和 `[lang] include_dirs` 解析。`#include <...>` 属于外部，忽略。

对改动文件里每个指向其他模块的导入：

1. 导入方所在模块的 May depend on 里列出了目标模块，否则 R07 失败。
2. 目标文件匹配目标模块的 External interfaces，否则 R07 失败，因为这个导入伸进了模块内部。

以下情况 R07 也失败：声明的 May depend on 关系图有环；或者整个仓库的导入在模块之间形成的环里，包含来自改动文件的导入。不属于任何模块的文件，例如测试和脚本，不检查。

## 8. Python 语言包

### 8.1 环境（D20）

遵循需求文档第 8 节的 Python 环境规则，参照 troy-voice 的做法：

- **系列。** 将来要在同一个平台上一起运行的项目组成一个系列。它们共用一个 mamba 环境，以系列命名，就像 troy-voice 的 `troy-agent-env`。不属于任何系列的项目，自成一个只有一个成员的系列，环境以项目自己命名。共用环境能让版本冲突在第二个项目需要某个包时就暴露出来，而不是等到平台第一次把它们一起加载时。
- `.troy-mode/config.toml` 写明环境名，并列出各成员在 Troy 电脑上的文件夹：

```toml
[lang]
environment = "troy-agent-env"
series = ["../troy-voice", "."]
```

- 每个成员的 `environment.yml` 都是同一个文件。mamba 只提供 Python 和 uv：

```yaml
name: <environment>
channels:
  - conda-forge
dependencies:
  - python=3.13
  - uv
```

- **每个系列一个锁文件。** `requirements-dev.lock` 固定所有成员的全部包版本，所以每个成员装的版本完全相同。它由所有成员的 `pyproject.toml` 一起编译生成，每个成员都提交同一份：

```text
uv pip compile ../troy-voice/pyproject.toml ./pyproject.toml --extra dev --universal -o requirements-dev.lock
```

- 在 Troy 的电脑上安装。前两行每个系列只运行一次，后面的每个成员运行一次：

```text
mamba env create -f environment.yml
mamba activate <environment>
uv pip install -r requirements-dev.lock
uv pip install -e . --no-deps
```

- CI 从本成员自己的那份锁文件安装，不需要其他成员。
- 不在已激活的 shell 里时，命令以 `mamba run -n <environment> <command>` 的方式运行。
- 从不创建 `.venv` 文件夹。
- 共用环境也有代价：一个成员升级，所有成员同时受影响。所以锁文件改动后，要先在共用环境里跑一遍所有成员的测试，再合并这个改动；其他成员通过各自的 PR 拿到新的锁文件。这一步的自动化属于 F07。

### 8.2 工具（D24）

`pyproject.toml` 片段增加一个 `dev` 可选依赖组，包含 ruff、mypy、pytest 和 coverage，并配置它们：

- **ruff** 使用 troy-voice 的规则集，外加 `D` 规则并设 `convention = "google"`，用来检查 docstring 的格式（R05）。它也检查代码格式。
- **mypy** 以严格模式运行，和 troy-voice 一样。
- **pytest** 在 `tests/` 里找测试，`addopts = "-ra --strict-markers"`。
- **coverage** 统计分支：`branch = true`，`source = ["src"]`。

### 8.3 命令

| 步骤 | 命令 |
| --- | --- |
| 代码检查和格式 | `ruff check` 和 `ruff format --check` |
| 类型 | `mypy` |
| 测试 | `coverage run -m pytest --junitxml=reports/junit.xml`。它的退出码被忽略，因为哪些失败是允许的由 troy-check 判断。 |
| 覆盖率报告 | `coverage xml -o reports/coverage.xml` |
| 规则 | `python .troy-mode/checks/troy_check.py code --base <ref> --title <title> --junit reports/junit.xml --coverage reports/coverage.xml` |

### 8.4 配置片段

```toml
[lang]
name = "python"
source_roots = ["src"]
environment = "<environment>"
series = ["."]

[paths]
tests = ["**/test_*.py", "**/*_test.py", "**/conftest.py"]
dependencies = ["pyproject.toml", "environment.yml", "requirements*.lock"]
lock = ["requirements*.lock"]
```

### 8.5 CI 任务

`workflow-job.yml` 往 F02 的项目工作流里加一个任务 `troy-mode code checks`。它检出完整历史，用固定到 commit SHA 的 `mamba-org/setup-micromamba` 创建环境，按锁文件安装，然后用 PR 的基点、head、标题和描述运行第 8.3 节的各个步骤。检出之后的第一步用 `git ls-files` 查看 PR 的 head 里 `src/` 下有没有文件。第一个 mock PR 之前没有，所以后面的步骤全部跳过，任务通过，摘要里写着“No code yet”（F06 设计 D50）。

## 9. C/C++ 语言包

### 9.1 工具链（D22）

- CMake 3.28 或更新版本，配合 Ninja。C++20 和 C17。
- GoogleTest 1.18.0，从发布包用项目自己的编译器编译（D25），通过 CTest 运行。
- 检查和覆盖率使用 GCC 和 gcov，由 gcovr 输出 Cobertura XML。
- CI 里用 Ubuntu 自带的 GCC。在 Troy 的电脑上用已经在 PATH 上的 MSYS2 GCC 15，所以本地也能跑同样的检查。
- Visual Studio 2026（MSVC）仍然可以通过单独的 CMake 预设 `msvc` 用来构建和调试。这个预设不统计覆盖率。

### 9.2 环境

```yaml
name: <environment>
channels:
  - conda-forge
dependencies:
  - python=3.13
  - uv
  - cmake
  - ninja
  - doxygen
  - clang-format=23
  - clang-tools=23
  - clang-23
```

mamba 提供非 Python 的工具，其中 clang-format 和 clang-tools 固定在同一个大版本，这样 CI 和 Troy 电脑上的格式化结果一致。clang-23 包含 clang 自己的头文件（如 `stddef.h`），clang-tidy 要读这些文件，而 clang-tools 不带它们。uv 从 `requirements-tools.lock` 安装 Python 工具 gcovr 和 lizard，这份锁文件由 `requirements-tools.in` 编译而来。编译器来自环境之外，见第 9.1 节，GoogleTest 也一样（D25）。系列、共用环境和系列锁文件的做法同第 8.1 节。

### 9.3 文档注释和格式（D21）

- 每个函数和类的声明上方都紧贴一段 `///`（或 `/** */`）注释。内容遵循 Google 的 C++ 风格：它做什么、参数、返回值和错误，用完整的句子写。
- 由 Doxygen 检查它们是否存在。语言包的 `Doxyfile` 设置 `WARN_IF_UNDOCUMENTED = YES`、`EXTRACT_PRIVATE = YES`、`EXTRACT_STATIC = YES` 和 `EXTRACT_ANON_NSPACES = YES`。troy-check 读取警告日志，保留落在改动行上的警告（R05）。
- 用 `BasedOnStyle: Google` 的 clang-format 检查改动文件的格式。
- clang-tidy 运行一小组查找 bug 的检查（`bugprone-*`、`performance-*`）。具体清单由开发工程师决定，记录在 `.clang-tidy` 里。

### 9.4 命令

| 步骤 | 命令 |
| --- | --- |
| 配置和构建 | `cmake --preset coverage` 和 `cmake --build --preset coverage` |
| 格式和代码检查 | 对改动文件运行 `clang-format --dry-run --Werror` 和 `clang-tidy` |
| 测试 | `ctest --preset coverage --output-junit reports/junit.xml`。它的退出码被忽略。 |
| 覆盖率报告 | `gcovr --cobertura reports/coverage.xml` |
| 文档注释 | `doxygen .troy-mode/lang/cpp/Doxyfile`，输出 `reports/doxygen.log` |
| 规则 | `python .troy-mode/checks/troy_check.py code ... --junit reports/junit.xml --coverage reports/coverage.xml --doc-warnings reports/doxygen.log` |

### 9.5 配置片段

```toml
[lang]
name = "cpp"
include_dirs = ["include", "src"]

[paths]
config = [".clang-format", ".clang-tidy", "include/troy/not_implemented.h"]
tests = ["**/*_test.cc", "**/*_test.cpp"]
dependencies = ["CMakeLists.txt", "**/CMakeLists.txt", "cmake/**", "CMakePresets.json",
                "environment.yml", "requirements*.lock", "requirements*.in"]
lock = ["requirements*.lock"]
```

CMake 文件算作依赖文件，因为添加库就是在这些文件里做的。依赖文件可以在源码 PR 和测试 PR 里修改（F02 设计 D9）。

### 9.6 CI 任务

和第 8.5 节类似，多一个配置和构建步骤。只在 Linux 上运行。它查看有没有代码时，看 `src/` 下，以及 `include/` 下除 `include/troy/` 以外的地方；`include/troy/` 里是语言包自己的头文件。

## 10. F03 怎么开发和测试

F03 分四个 PR 合入，每个 PR 一个 commit，都先写测试（D15）：

1. **引擎：测试和覆盖率。** R09、R10、R11、`code` 子命令，以及 R01 的标题行检查。测试使用手写的小 JUnit 和 Cobertura 文件。
2. **引擎：代码形态。** R04 到 R07，以及 Python 适配器。
3. **Python 语言包。** 第 8 节的文件，加上一个小的 Python 示例项目，由 CI 带着它走完整个语言包：环境、测试、覆盖率和 `troy-check code`。
4. **C/C++ 语言包。** C/C++ 适配器和第 9 节的文件，加上一个小的 C++ 示例项目，由 CI 带着它走完语言包。

troy-pstack 的 CI 在 Linux 和 Windows 上跑单元测试，在 Linux 上跑示例项目。在 Troy 的电脑上，用 troy-pstack 自己的环境 `troy-pstack` 来跑（D26）。

PR 4 合并后，F03 的状态改为"已编写"。两个示例项目都在 CI 里跑通后，改为"在示例项目上跑通"。

## 11. 不属于 F03 的内容

- TypeScript/JavaScript 语言包。以后按同样的结构来做。
- 把语言包复制进项目、选择项目语言（F06）。
- 性能测试。R14 是审查规则，性能测试在版本发布时运行（Q7）。
- 告诉测试工程师怎么给测试命名、告诉开发工程师怎么写 mock 的角色指令（F04）。
- 依赖改动后，更新系列里每个成员的锁文件，并在共用环境里重跑每个成员的测试（F07）。

## 12. 需要 Troy 决定的事项

Troy 已于 2026-11-05 批准全部十项提议，其中 D20 修改过一次。2026-11-06 做第 4 部分时，Troy 又决定了 D25 和 D26。

| 编号 | 待决定的事 | 提议 |
| --- | --- | --- |
| D15 | F03 的结构和交付方式。 | 与语言无关的引擎，加上很薄的语言包，见第 1 节。F03 负责没有归属的 R09。分四个 PR 合入（第 10 节），作为 Q10"每个功能一个 PR"的例外，因为一个 PR 会装下两个语言包和整个引擎。 |
| D16 | 测试怎么带上编号（R10）。 | 测试自己的名字以用例编号或 bug 编号开头（第 4.1 节）。每种语言的测试名都能通过 JUnit XML 交给 troy-check。如果用测试框架的标记，就得为每种语言各写一个读取器。 |
| D17 | troy-check 怎么知道哪些功能已验收、哪些 bug 已修复。 | 从基点的历史里读取：标题行为 `[F04 6/6 accept]` 和 `[B12 B/B fix]` 的 commit。R01 同时要求 commit 的标题行等于 PR 标题。这样离线也能用，不需要调用 GitHub。 |
| D18 | R11 怎么统计改动行的覆盖率。 | troy-check 自己读取 Cobertura XML，不需要 diff-cover 这类第三方工具。排除注释必须在同一行写 `reason:`。 |
| D19 | R07 的模块映射从哪里来，由哪个工具检查。 | 来自 `docs/architecture.md` 第 3 节的模块表，让架构文档保持唯一的事实来源。两种语言都用 troy-check 自己的检查器，Python 不再用 import-linter。架构模板要求在 Owns 和 External interfaces 两列里填路径规则。 |
| D20 | Python 环境。troy-voice 在多个项目之间共用一个环境 `troy-agent-env`，也没有锁文件。 | 根据 Troy 2026-11-05 的回复修改。Troy 同意加锁文件，并希望同一系列的项目共用一个环境，以免用它们搭平台时出现版本冲突。因此：每个系列一个环境，每个系列一个 `requirements-dev.lock`，由所有成员的 `pyproject.toml` 一起编译，每个成员各提交一份（第 8.1 节）。如果在共用环境里每个项目各锁各的，成员之间就可能把同一个包锁成不同版本。Troy 已于同日批准修改后的方案。 |
| D21 | C/C++ 的文档注释。Google 的 C++ 风格用普通的 `//` 注释，任何工具都没法把它和其他注释区分开。 | 用 `///` 注释，内容按 Google 风格写，这样 Doxygen 就能报告哪些没写文档。 |
| D22 | 检查用的 C/C++ 编译器。 | 各处都用 GCC 和 gcov，因为覆盖率需要它们：CI 用 Ubuntu 的 GCC，你的电脑用 MSYS2 GCC 15。Visual Studio 2026 的 MSVC 仍然可以用来构建和调试，只是不统计覆盖率。 |
| D23 | "注释只用英文"（R05）对脚本来说具体指什么。 | 注释和文档注释里不出现中文、日文或韩文字符：CJK 汉字、假名、韩文字母，以及 CJK 和全角标点。其他非 ASCII 文字，例如带重音符号的名字和 → 这类符号，允许使用。 |
| D24 | R 规则之外的 Python 工具。 | 语言包沿用 troy-voice 的默认做法：范围很广的 ruff 规则集、ruff 的格式检查，以及严格模式的 mypy。项目可以通过规则变更流程去掉它们。 |
| D25 | GoogleTest 从哪里来。第 9.2 节原本把它放进 mamba 环境，但 conda-forge 在 Windows 上的 GoogleTest 是 MSVC 编译的，MSYS2 GCC 链接不了，这一点已在 Troy 的电脑上实测。 | `cmake/troy.cmake` 用 CMake 的 FetchContent 下载 GoogleTest 1.18.0 的发布包，校验 SHA256，再用项目自己的编译器编译。CI 和 Troy 的电脑用同一个版本。Troy 于 2026-11-06 选定这个方案，没有选各平台的包管理器，也没有选在本机改用 MSVC。 |
| D26 | troy-pstack 自己的测试从哪里拿到 lizard（C/C++ 适配器需要它）。之前这些测试用系统 Python 跑。 | troy-pstack 自成一个系列，有自己的环境 `troy-pstack`，由 `troy-mode/dev/environment.yml` 创建，lizard 和 gcovr 按 `troy-mode/dev/requirements-dev.lock` 安装。环境里也有 C/C++ 工具，所以 C++ 示例能在 Troy 的电脑上跑。CI 安装同一份锁文件。Troy 于 2026-11-06 选定。 |

需求文档 1.6 记录了批准后的修改：

- F03 那一行加上 R09、引擎和语言包，以及四个 PR（D15）。
- R01 加上标题行检查（D17）。R10 写明测试怎么带编号（D16）。规则模板随之更新。
- 第 8 节的 Python 环境规则加上系列、每个系列一个环境、每个系列一个锁文件（D20）。

架构模板第 3 节的填写说明随需求文档 1.6 一起修改（D19）。

## 13. 修改记录

| 版本 | 日期 | 修改 |
| --- | --- | --- |
| 0.1 | 2026-11-05 | 初稿。 |
| 0.2 | 2026-11-05 | Troy 批准了 D15 到 D24，D20 除外。D20 已修改：每个系列一个环境、一个锁文件（第 8.1 节）。 |
| 1.0 | 2026-11-05 | Troy 批准，含 D15 到 D24，D20 按修改后的方案。 |
| 1.1 | 2026-11-06 | 加入 Troy 在做第 4 部分时决定的 D25 和 D26。GoogleTest 移出环境（第 9.1、9.2 节），clang-format 和 clang-tools 固定在 23 版，环境加入供 clang-tidy 使用的 clang-23，第 2 节列出示例项目和 troy-pstack 自己的环境。 |
| 1.2 | 2026-11-07 | F06 已批准设计带来的修改（F06 设计第 8 节）。PR 的 head 里还没有代码时，两个语言包的 CI 任务跳过代码步骤（F06 D50，第 8.5、9.6 节）。C/C++ 的配置片段把 `include/troy/not_implemented.h` 放进 `config`（F06 D49），并列出 `requirements*.in`（第 9.5 节）。每个语言包多了一个新项目用的构建文件（第 2 节）。`build_sample.py` 通过 troy-init 自己的函数初始化示例项目，每个示例多了一个没有代码的设计 PR。 |
