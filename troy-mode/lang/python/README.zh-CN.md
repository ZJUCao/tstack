# troy-mode Python 语言包

> 本文件是 [`README.md`](README.md) 的中文镜像，同步自英文版 1.0（2026-11-06）。两者如有出入，以英文版为准。

| | |
| --- | --- |
| 版本 | 1.0 |
| 日期 | 2026-11-06 |
| 事实来源 | 英文版 [`README.md`](README.md)。本文件是中文镜像。 |

Python 语言包让 troy-check 的语言相关规则在 Python 项目里运行：R04 到 R07 检查代码，R09 到 R11 检查测试结果。`troy-init`（F06）把它复制到项目里。[F03 设计](../../../docs/troy-mode/design/F03-language-packs.zh-CN.md)第 8 节记录了每个选择的理由。

## 1. 文件

| 文件 | 在项目里的位置 | 内容 |
| --- | --- | --- |
| [`environment.yml`](environment.yml) | `environment.yml` | 系列环境：来自 conda-forge 的 Python 3.13 和 uv。`troy-init` 填写 `{{environment}}`。 |
| [`pyproject.toml`](pyproject.toml) | 追加到 `pyproject.toml` 末尾 | `dev` 依赖组（coverage、mypy、pytest、ruff）和这些工具的设置。 |
| [`config.toml`](config.toml) | 加进 `.troy-mode/config.toml` | `[lang]` 和 Python 的路径规则。 |
| [`workflow-job.yml`](workflow-job.yml) | 加到 `.github/workflows/troy-mode.yml` 的 `jobs:` 下 | `troy-mode code checks` 这个 CI 任务。 |

项目还要提交 `requirements-dev.lock`（第 2 节），并在 `.gitignore` 里列出 `reports/`、`.coverage` 和 mypy、pytest、ruff 的缓存。

## 2. 环境

将来要在同一个平台上一起运行的项目组成一个系列，共用一个以系列命名的 mamba 环境。不属于任何系列的项目自成一个系列。mamba 只提供 Python 和 uv，其余所有包都由 uv 按 `requirements-dev.lock` 安装，系列里的每个项目都提交这同一份锁文件。任何时候都不建 `.venv` 文件夹。

锁文件由系列里所有项目的 `pyproject.toml` 一起编译出来。只有一个项目的系列这样编译：

```text
uv pip compile pyproject.toml --extra dev --universal -o requirements-dev.lock
```

在 Troy 电脑上的安装步骤。前两行每个系列运行一次，其余每个项目运行一次：

```text
mamba env create -f environment.yml
mamba activate <environment>
uv pip install -r requirements-dev.lock
uv pip install -e . --no-deps
```

## 3. 命令

在激活的环境里运行，或者写成 `mamba run -n <environment> <命令>`。

| 步骤 | 命令 |
| --- | --- |
| 代码规范和格式 | `ruff check` 和 `ruff format --check` |
| 类型检查 | `mypy` |
| 测试 | `coverage run -m pytest --junitxml=reports/junit.xml`。测试失败不会让任务停下：哪些失败是允许的，由 troy-check 判断。 |
| 覆盖率报告 | `coverage xml -o reports/coverage.xml` |
| 规则检查 | `python .troy-mode/checks/troy_check.py code --base <ref> --title <标题> --junit reports/junit.xml --coverage reports/coverage.xml` |

## 4. 工具设置

- **ruff** 沿用 troy-voice 的规则集，再加上 Google 风格的 `D` 规则，用来检查 docstring（R05）。它跳过 `.troy-mode`，因为 troy-check 在 troy-pstack 里检查。它忽略 RUF001，所以字符串里可以有中文标点。RUF002 和 RUF003 保持开启，因为 R05 本来就不允许 docstring 和注释里出现中文。测试可以用 `assert`，也不需要类型标注。
- **mypy** 用严格模式检查 `src`。
- **pytest** 在 `tests/` 里找测试，参数是 `-ra --strict-markers`。
- **coverage** 统计 `src` 里的行覆盖和分支覆盖。

项目自己的设置，比如 troy-voice 禁用的时间函数，加在语言包的设置后面。要去掉语言包的某项设置，走规则变更流程。

## 5. CI 任务

这个任务检出 PR 及其完整历史，用固定到某个提交的 `mamba-org/setup-micromamba` 创建环境，按锁文件安装，然后运行第 3 节的步骤。和 F02 的 troy-check 任务一样，PR 的标题和描述只通过环境变量传给 shell；基准提交里有 troy-check 时，就用基准提交里的那份运行，所以 PR 改不了评判它的代码。

## 6. 示例项目

[`troy-mode/samples/python`](../../samples/python) 里是 textstats，一个很小的项目，它的功能 F01 依次经过设计、测试计划、mock、测试和实现。[`build_sample.py`](../../dev/build_sample.py) 按 `troy-init` 初始化项目的方式建出它的 git 仓库。然后 troy-pstack 的工作流 `troy-python-sample.yml` 在两个 PR 上运行第 5 节的步骤：

- 测试 PR：每个新测试都必须在 mock 上失败（R09）；
- 实现 PR：所有测试都通过，改动的代码行都被测试覆盖（R11）。

`troy-mode/dev/tests/test_python_pack.py` 检查示例的工作流和 `workflow-job.yml` 运行的是同样的步骤。自己构建示例：

```text
python troy-mode/dev/build_sample.py build python --pr impl --out <空文件夹>
```
