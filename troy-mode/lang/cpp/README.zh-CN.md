# troy-mode C/C++ 语言包

> 本文件是 [`README.md`](README.md) 的中文镜像，同步自英文版 1.1（2026-11-07）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 1.1 |
| 日期 | 2026-11-07 |
| 事实来源 | 英文版 [`README.md`](README.md)。本文件是中文镜像。 |

C/C++ 语言包让 troy-check 的语言相关规则在 C 或 C++ 项目里运行：R04 到 R07 检查代码，R09 到 R11 检查测试结果。`troy-init`（F06）把它复制到项目里。[F03 设计](../../../docs/troy-mode/design/F03-language-packs.zh-CN.md)第 9 节记录了每个选择的理由。

## 1. 文件

| 文件 | 在项目里的位置 | 内容 |
| --- | --- | --- |
| [`environment.yml`](environment.yml) | `environment.yml` | 系列环境：来自 conda-forge 的 Python、uv、CMake、Ninja、Doxygen、clang-format 和 clang-tidy。`troy-init` 填写 `{{environment}}`。 |
| [`requirements-tools.in`](requirements-tools.in) | `requirements-tools.in` | Python 工具 gcovr 和 lizard，编译成 `requirements-tools.lock`。 |
| [`CMakePresets.json`](CMakePresets.json) | `CMakePresets.json` | 检查用的 `coverage` 预设，和用于构建、调试的 `msvc` 预设。 |
| [`cmake/troy.cmake`](cmake/troy.cmake) | `cmake/troy.cmake` | 语言标准、编译警告、覆盖率、GoogleTest、`troy_add_test`，以及 `troy_add_version_test`。 |
| [`Doxyfile`](Doxyfile) | `.troy-mode/lang/cpp/Doxyfile` | 用 Doxygen 检查文档注释。 |
| [`.clang-format`](.clang-format) | `.clang-format` | Google 风格。 |
| [`.clang-tidy`](.clang-tidy) | `.clang-tidy` | 找 bug 的检查项。 |
| [`include/troy/not_implemented.h`](include/troy/not_implemented.h) | `include/troy/not_implemented.h` | `troy::NotImplemented`，mock 的函数体抛出它。 |
| [`config.toml`](config.toml) | 加进 `.troy-mode/config.toml` | `[lang]` 和 C/C++ 的路径规则。 |
| [`workflow-job.yml`](workflow-job.yml) | 加到 `.github/workflows/troy-mode.yml` 的 `jobs:` 下 | `troy-mode code checks` 这个 CI 任务。 |
| [`CMakeLists-project.txt`](CMakeLists-project.txt) | 项目没有 `CMakeLists.txt` 时，作为 `CMakeLists.txt` | `cmake_minimum_required(VERSION 3.28)`、`project(<name> C CXX)` 和 `include(cmake/troy.cmake)`。`troy-init` 填写 `{{project-name}}`。 |

顶层 `CMakeLists.txt` 在 `project()` 之后立刻引入 `cmake/troy.cmake`，每个测试程序都用 `troy_add_test` 添加。项目还要提交 `requirements-tools.lock`（第 2 节），并在 `.gitignore` 里列出 `build/` 和 `reports/`。

## 2. 环境

- 环境的用法和 Python 语言包一样：每个系列一个 mamba 环境，每个系列一份锁文件。任何时候都不建 `.venv` 文件夹。
- mamba 提供构建工具。clang-format 和 clang-tools 固定在同一个大版本，这样 CI 和 Troy 电脑上的格式化结果一致。
- 环境里还有 clang-23，它包含 clang 自己的头文件（如 `stddef.h`）。clang-tidy 要读这些文件，而 clang-tools 不带它们。缺了它们，clang-tidy 在 Linux 上会失败。
- uv 按 `requirements-tools.lock` 安装 gcovr 和 lizard。
- 编译器不在环境里：CI 用 Ubuntu 自带的 GCC，Troy 的电脑用 PATH 上的 MSYS2 GCC。
- GoogleTest 也不在环境里。`cmake/troy.cmake` 下载它的发布包，校验 SHA256，再用项目自己的编译器编译（设计 D25）。conda-forge 在 Windows 上的 GoogleTest 是 MSVC 编译的，GCC 链接不了。

只有一个项目的系列这样编译锁文件：

```text
uv pip compile requirements-tools.in --universal --python-version 3.13 -o requirements-tools.lock
```

在 Troy 电脑上的安装步骤。前两行每个系列运行一次，其余每个项目运行一次：

```text
mamba env create -f environment.yml
mamba activate <environment>
uv pip install -r requirements-tools.lock
cmake --preset coverage
```

## 3. 命令

在激活的环境里运行，或者写成 `mamba run -n <environment> <命令>`。

| 步骤 | 命令 |
| --- | --- |
| 配置和构建 | `cmake --preset coverage` 和 `cmake --build --preset coverage` |
| 格式和静态检查 | 对改动的文件运行 `clang-format --dry-run --Werror`，对改动的源文件运行 `clang-tidy -p build/coverage` |
| 测试 | `ctest --preset coverage --output-junit <绝对路径>/reports/junit.xml`。测试失败不会让任务停下：哪些失败是允许的，由 troy-check 判断。相对路径会被 CTest 当成相对于构建目录。 |
| 覆盖率报告 | `gcovr --root . --filter 'include/' --filter 'src/' --exclude-throw-branches --exclude-unreachable-branches --cobertura reports/coverage.xml build/coverage` |
| 文档注释 | `doxygen .troy-mode/lang/cpp/Doxyfile`，它会写出 `reports/doxygen.log` |
| 规则检查 | `python .troy-mode/checks/troy_check.py code --base <ref> --title <标题> --junit reports/junit.xml --coverage reports/coverage.xml --doc-warnings reports/doxygen.log` |
| 发布命令（版本测试，只在发布时运行） | `cmake --preset coverage -DTROY_VERSION_TESTS=ON`、`cmake --build --preset coverage`，然后 `ctest --preset coverage -L version --output-junit <绝对路径>/reports/version-junit.xml`。版本测试失败不会让它停下：发布测试会报告它。 |

C/C++ 项目里 troy-check 要用 lizard，所以要用环境里的 Python 运行。

## 4. 工具设置

- **文档注释。** 每个函数和类的声明正上方都要有 `///` 或 `/** */` 注释，按 Google 风格用完整的句子写：它做什么、参数、返回值、会出什么错。没有注释的声明都会被 Doxygen 警告，私有的和静态的也不例外。`.cc` 文件里的定义，只要它的声明已经有注释，就不用再写。
- **覆盖率。** `coverage` 预设用 GCC 加 `--coverage` 和 `-O0` 构建。gcovr 不统计只有异常才会走的分支：每个可能抛异常的调用都会多出这样一个分支，测试大多走不到。
- **编译警告。** GCC 用 `-Wall -Wextra -Wpedantic`，MSVC 用 `/W4 /permissive-`。用 MinGW 时，程序静态链接 GCC 运行库，这样就不会加载 PATH 上排在前面的另一份 GCC 的 DLL，比如 Git for Windows 自带的那份。
- **clang-tidy** 运行 `bugprone-*` 和 `performance-*`，去掉 `bugprone-easily-swappable-parameters`，所有发现都按错误处理。
- **C++20 模块**关闭，因为它的 GCC 参数会让 clang-tidy 出错。
- **测试**是 GoogleTest 测试，名字以测试用例编号开头，比如 `TEST(ExportCsv, F04_T07_WritesHeader)`。`troy_add_test` 把每个测试单独注册到 CTest，这样每个测试的名字都会出现在 JUnit 报告里。
- **版本测试**放在 `version-tests/` 里，名字以场景编号开头，比如 `TEST(Version, V0_1_S01_CountsWordsAndLines)`。`troy_add_version_test` 只在那一次配置设了 `TROY_VERSION_TESTS=ON` 时才构建它们，并给它们打上 `version` 标签，所以每个 PR 的检查都不包含它们（F08 设计第 5.3 节）。

## 5. CI 任务

这个任务检出 PR 及其完整历史，然后用 `git ls-files` 查看 PR 的最新提交里 `src/` 下，或 `include/` 下除 `include/troy/` 以外，有没有文件。第一个 mock PR 之前没有，所以后面的步骤全部跳过，任务通过，摘要里写着“No code yet”（F06 设计 D50）。有代码时，它用固定到某个提交的 `mamba-org/setup-micromamba` 创建环境，按锁文件安装，然后在 Linux 上运行第 3 节的步骤。和 F02 的 troy-check 任务一样，PR 的标题和描述只通过环境变量传给 shell；基准提交里有 troy-check 时，就用基准提交里的那份运行。

## 6. 示例项目

[`troy-mode/samples/cpp`](../../samples/cpp) 里是 C++ 版的 textstats，F01 和 Python 示例相同，另外多一个文件读不了的测试用例。troy-pstack 的工作流 `troy-cpp-sample.yml` 用 [`build_sample.py`](../../dev/build_sample.py) 通过 `troy-init` 自己的初始化和语言步骤构建它，然后在三个 PR 上运行第 5 节的步骤：设计 PR（还没有代码，跳过代码步骤）、测试 PR 和实现 PR。`troy-mode/dev/tests/test_cpp_pack.py` 检查示例的工作流和 `workflow-job.yml` 运行的是同样的步骤。自己构建示例：

```text
python troy-mode/dev/build_sample.py build cpp --pr impl --out <空文件夹>
```
