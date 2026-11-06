# troy-mode C/C++ pack

| | |
| --- | --- |
| Version | 1.0 |
| Date | 2026-11-06 |
| Source of truth | This English file. [`README.zh-CN.md`](README.zh-CN.md) is the Chinese mirror. |

The C/C++ pack makes troy-check's language rules run in a C or C++ project: R04 to R07 on the code, and R09 to R11 on the test run. `troy-init` (F06) copies it into a project. [The F03 design](../../../docs/troy-mode/design/F03-language-packs.md), section 9, records why each choice was made.

## 1. Files

| File | Where it lands in the project | What it holds |
| --- | --- | --- |
| [`environment.yml`](environment.yml) | `environment.yml` | The series environment: Python, uv, CMake, Ninja, Doxygen, clang-format, and clang-tidy from conda-forge. `troy-init` fills in `{{environment}}`. |
| [`requirements-tools.in`](requirements-tools.in) | `requirements-tools.in` | The Python tools, gcovr and lizard, compiled into `requirements-tools.lock`. |
| [`CMakePresets.json`](CMakePresets.json) | `CMakePresets.json` | The `coverage` preset for the checks, and the `msvc` preset for building and debugging. |
| [`cmake/troy.cmake`](cmake/troy.cmake) | `cmake/troy.cmake` | Language standards, warnings, coverage, GoogleTest, and `troy_add_test`. |
| [`Doxyfile`](Doxyfile) | `.troy-mode/lang/cpp/Doxyfile` | Doxygen as the doc comment checker. |
| [`.clang-format`](.clang-format) | `.clang-format` | Google style. |
| [`.clang-tidy`](.clang-tidy) | `.clang-tidy` | Bug-finding checks. |
| [`include/troy/not_implemented.h`](include/troy/not_implemented.h) | `include/troy/not_implemented.h` | `troy::NotImplemented`, which a mock's function bodies throw. |
| [`config.toml`](config.toml) | Added to `.troy-mode/config.toml` | `[lang]` and the C/C++ path patterns. |
| [`workflow-job.yml`](workflow-job.yml) | Added under `jobs:` in `.github/workflows/troy-mode.yml` | The `troy-mode code checks` job. |

The top-level `CMakeLists.txt` includes `cmake/troy.cmake` right after `project()`, and adds each test executable with `troy_add_test`. The project also commits `requirements-tools.lock` (section 2), and its `.gitignore` lists `build/` and `reports/`.

## 2. Environment

- The environment works as in the Python pack: one mamba environment per series, and one lock per series. No `.venv` folder is ever created.
- mamba provides the build tools. clang-format and clang-tools are pinned to one major version, so CI and Troy's PC format code the same way.
- The environment also has clang-23, which holds clang's own headers, such as `stddef.h`. clang-tidy reads them, and clang-tools does not include them. Without them clang-tidy fails on Linux.
- uv installs gcovr and lizard from `requirements-tools.lock`.
- The compiler comes from outside the environment: Ubuntu's GCC in CI, and on Troy's PC the MSYS2 GCC that is on the PATH.
- GoogleTest is not in the environment. `cmake/troy.cmake` downloads its release archive, checks the archive's SHA256, and builds it with the project's own compiler (design D25). conda-forge's GoogleTest for Windows is built with MSVC, and GCC cannot link it.

Compile the lock for a series of one:

```text
uv pip compile requirements-tools.in --universal --python-version 3.13 -o requirements-tools.lock
```

Setup on Troy's PC. The first two lines run once per series, the rest once per member:

```text
mamba env create -f environment.yml
mamba activate <environment>
uv pip install -r requirements-tools.lock
cmake --preset coverage
```

## 3. Commands

Run them in the activated environment, or as `mamba run -n <environment> <command>`.

| Step | Command |
| --- | --- |
| Configure and build | `cmake --preset coverage` and `cmake --build --preset coverage` |
| Format and lint | `clang-format --dry-run --Werror` on changed files, and `clang-tidy -p build/coverage` on changed source files |
| Tests | `ctest --preset coverage --output-junit <absolute path>/reports/junit.xml`. Failing tests do not stop the job: troy-check decides which failures are allowed. CTest reads a relative path from the build folder. |
| Coverage report | `gcovr --root . --filter 'include/' --filter 'src/' --exclude-throw-branches --exclude-unreachable-branches --cobertura reports/coverage.xml build/coverage` |
| Doc comments | `doxygen .troy-mode/lang/cpp/Doxyfile`, which writes `reports/doxygen.log` |
| Rules | `python .troy-mode/checks/troy_check.py code --base <ref> --title <title> --junit reports/junit.xml --coverage reports/coverage.xml --doc-warnings reports/doxygen.log` |

troy-check needs lizard in a C/C++ project, so it runs with the environment's Python.

## 4. Tool settings

- **Doc comments.** Every function and class declaration has a `///` or `/** */` comment directly above it, written in full sentences in Google's style: what it does, its parameters, its return value, and its errors. Doxygen warns about every declaration without one, private and static ones included. A definition in a `.cc` file needs no comment of its own when its declaration has one.
- **Coverage.** The `coverage` preset builds with GCC, `--coverage`, and `-O0`. gcovr leaves out the branches that only exceptions take, because every call that may throw adds such a branch, and no test can reach most of them.
- **Warnings.** GCC runs with `-Wall -Wextra -Wpedantic`, and MSVC with `/W4 /permissive-`. With MinGW, programs link the GCC runtime statically, so they never load another GCC's DLL that comes first on the PATH, such as Git for Windows' copy.
- **clang-tidy** runs `bugprone-*` and `performance-*`, without `bugprone-easily-swappable-parameters`, and treats every finding as an error.
- **C++20 modules** are off, because their GCC flags stop clang-tidy.
- **Tests** are GoogleTest tests whose names start with the case ID, for example `TEST(ExportCsv, F04_T07_WritesHeader)`. `troy_add_test` registers each test with CTest on its own, so each name reaches the JUnit report.

## 5. CI job

The job checks out the PR with its full history, creates the environment with `mamba-org/setup-micromamba` pinned to a commit, and installs from the lock. Then it runs the steps of section 3 on Linux. As in the troy-check job from F02, the PR's title and description reach the shell only through environment variables, and troy-check runs from the base commit when it exists there.

## 6. Sample project

[`troy-mode/samples/cpp`](../../samples/cpp) holds textstats in C++, with the same F01 as the Python sample plus one case for a file that cannot be read. troy-pstack's workflow `troy-cpp-sample.yml` builds it with [`build_sample.py`](../../dev/build_sample.py) and runs the steps of section 5 on its tests PR and its implementation PR. `troy-mode/dev/tests/test_cpp_pack.py` checks that the sample's workflow runs the same steps as `workflow-job.yml`. To build the sample yourself:

```text
python troy-mode/dev/build_sample.py build cpp --pr impl --out <empty folder>
```
