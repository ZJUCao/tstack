# F03 design: language packs

| | |
| --- | --- |
| Feature | F03 in [requirements 1.6](../requirements.md#72-feature-list) |
| Version | 1.1 |
| Date | 2026-11-06 |
| Status | Approved by Troy on 2026-11-05, with D15 to D24. Version 1.1 adds D25 and D26, which Troy chose on 2026-11-06. |
| Source of truth | This English file. [`F03-language-packs.zh-CN.md`](F03-language-packs.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F03 makes troy-check enforce the rules that depend on a project's language:

| Rule | What F03 checks | Applies to |
| --- | --- | --- |
| R04 | A function body has at most 50 code lines. | Changed functions |
| R05 | Every function and class has a Google-style doc comment. Comments and doc comments hold no Chinese, Japanese, or Korean text. | Changed functions and changed lines |
| R06 | A source file has at most 500 lines (soft). | Changed source files |
| R07 | Modules depend on each other only in allowed directions, only through external interfaces, and never in a cycle. | Imports in changed files |
| R09 | Every new test in a test PR fails against the mock. | Tests of the PR's feature or bug |
| R10 | Every test carries its case ID or bug ID. Only tests of features not yet accepted and of bugs not yet fixed may fail. | All tests |
| R11 | Changed code has at least 90% line and 80% branch coverage. | Changed lines in `impl` and `fix` PRs |

The requirements list R09 under no feature. F02's design left it to F03, so F03 takes it (D15).

Following Q6, R04 to R07 and R11 look only at new and changed code. Old code is fixed when it is touched.

F03 has two parts (D15):

1. **The engine.** Language-independent code in troy-check, standard library only. It reads test results as JUnit XML, coverage as Cobertura XML, and source files through one small adapter per language. Nearly every test runner and coverage tool can write these two formats.
2. **Language packs.** Python first, then C/C++. A pack holds the environment, the tool configuration, the commands that build and test, the CI job, the path patterns for F02's config, and the adapter.

A TypeScript/JavaScript pack can later take the same shape. It is not designed here.

## 2. Location

```text
troy-mode/
  checks/
    troycheck/          F02's modules plus the engine (internal modules: the Developer's choice)
  lang/
    python/
      README.md         README.zh-CN.md
      environment.yml   pyproject.toml (fragment)   config.toml (fragment)   workflow-job.yml
    cpp/
      README.md         README.zh-CN.md
      environment.yml   requirements-tools.in   CMakePresets.json   cmake/troy.cmake   Doxyfile
      .clang-format     .clang-tidy         config.toml (fragment)   workflow-job.yml
      include/troy/not_implemented.h   (the exception that mock bodies throw)
  samples/
    python/  cpp/      sample projects that troy-pstack's CI takes through each pack (section 10)
  dev/
    build_sample.py    builds a sample's git repository
    environment.yml    requirements-dev.lock   troy-pstack's own environment (D26)
```

Each pack README lists its files, where they land in a project, and the commands in sections 8.3 and 9.4. `troy-init` (F06) copies the chosen pack into a project.

## 3. Command-line interface: `troy-check code`

```text
python .troy-mode/checks/troy_check.py code --base <ref> [--head <ref>] --title <text> [--body-file <path>] [--junit <path>]... [--coverage <path>]... [--doc-warnings <path>] [--repo <path>] [--json]
```

| Option | Meaning |
| --- | --- |
| `--base`, `--head`, `--title`, `--body-file`, `--repo`, `--json` | As in `pr` (F02 design section 3.1). |
| `--junit` | A JUnit XML file from the test run. It may be given more than once. Without it, R09 and R10 are `skip`. |
| `--coverage` | A Cobertura XML file from the coverage tool. It may be given more than once. Without it, R11 is `skip`. |
| `--doc-warnings` | C/C++ only: Doxygen's warning log, used by R05 (section 9.3). |

The report and exit codes are those of F02 design section 3.3. Results come in the order R04, R05, R06, R07, R09, R10, R11. CI always passes `--junit` and `--coverage`, so a `skip` there means a broken workflow, not a passed rule.

`[lang] name` in `.troy-mode/config.toml` selects the adapter: `"python"` or `"cpp"`. Like the rest of the config, it is read from the merge-base commit.

The C/C++ adapter needs lizard (section 6), so in a C/C++ project `troy-check code` runs with the project environment's Python. The Python adapter uses the standard library only.

F03 also changes F02's `pr` subcommand: R01 now also checks that the commit's subject line equals the PR title (D17).

## 4. Test names and test policy (R09, R10)

### 4.1 Tags (D16)

A test's own name starts with its case ID from the test plan, or with its bug ID. troy-check reads test names from the JUnit XML, so tagging works the same way in every language.

| Language | Feature test | Bug test |
| --- | --- | --- |
| Python (pytest) | `def test_f04_t07_writes_header():` | `def test_b12_empty_history_does_not_crash():` |
| C++ (GoogleTest) | `TEST(ExportCsv, F04_T07_WritesHeader)` | `TEST(History, B12_EmptyHistoryDoesNotCrash)` |

- The own name is the JUnit test name without a `test_` prefix, without a parameter suffix in brackets, and, for GoogleTest, without the suite name.
- Matching ignores case and treats `-` and `_` alike, so `f04_t07`, `F04_T07`, and `F04-T07` are the same case.
- A test whose name holds no ID fails R10. The exception is files matched by the `[tests] legacy` patterns, for a project that adopts troy-mode with tests it already has (Q6).
- R10 also compares the tests with the feature's test plan at `docs/features/<feature-id>-<slug>/test-plan.md`. A planned case with no test, or a test whose case is not in the plan, is a `warn` for the Test Manager.

### 4.2 Which tests may fail

Accepted features and fixed bugs come from the history of the merge-base commit (D17):

- A commit whose subject starts with `[F04 6/6 accept]` accepts F04.
- A commit whose subject starts with `[B12 B/B fix]` fixes B12.

This works because each PR has one commit (R01), and F03 makes R01 also require that commit's subject to equal the PR title. Rebase merges keep the subject on `main`.

| PR kind | Must fail (R09) | Must pass (R10) | May fail |
| --- | --- | --- | --- |
| `tests` for F04 | Every F04 test | Tests of accepted features and fixed bugs | Any other test |
| `test` for bug B12 | Every B12 test | Tests of accepted features and fixed bugs | Any other test |
| `impl` or `accept` for F04 | None | F04's tests, plus those above | Any other test |
| `fix` for B12 | None | B12's tests, plus those above | Any other test |
| Any other kind | None | Tests of accepted features and fixed bugs | Any other test |

- A JUnit failure or error counts as failing. A skipped test counts as not passing, so a skip cannot hide a must-pass test, and it cannot stand in for a must-fail test either.
- A missing JUnit file, or one that reports a collection or build error, fails R10.
- A mock's function bodies only signal that they are not implemented (`raise NotImplementedError` in Python, `throw troy::NotImplemented{}` in C++). So every test of a new interface fails against the mock, as R09 expects.

## 5. Coverage (R11)

- Applies to `impl` and `fix` PRs. Skipped for other kinds.
- Changed lines are lines added or modified in `source` files (F02 design section 5), from `git diff -U0` between the merge base and the head.
- In the Cobertura XML, a changed line that the report lists is executable. Line coverage is covered executable changed lines divided by executable changed lines. Branch coverage is covered branch outcomes divided by all branch outcomes on changed lines, read from each line's `condition-coverage`.
- The limits are `[limits] line_coverage = 90` and `branch_coverage = 80`. A PR with no executable changed lines passes.
- File paths in the report are resolved against its `<source>` roots, so they match repository paths.
- An excluded line needs a reason on the same line (D18), for example `# pragma: no cover  reason: a full disk cannot be simulated` or `// GCOVR_EXCL_LINE reason: ...`. An exclusion comment on a changed line without `reason:` fails R11. The Test Manager approves the reason in review.

## 6. Code shape (R04, R05, R06)

Each adapter reads one source file and returns its functions and classes (name, line range, body line range, whether a doc comment is attached) and its comments (line and text, doc comments included).

- **R04.** For each function whose range touches a changed line, count body lines that hold code: not blank, not a comment, not a doc comment. More than `[limits] function_lines = 50` fails.
- **R05.** Every function and class that touches a changed line has a doc comment. The doc comment's format is checked by the language's own tool (sections 8.2 and 9.3). Comments and doc comments on changed lines must not contain Chinese, Japanese, or Korean characters (D23). String literals may hold any text.
- **R06.** A changed source file with more than `[limits] file_lines = 500` lines is a `warn` when the description's "Soft-limit reason" section gives a reason, and a `fail` when it does not, exactly like R03.

| Adapter part | Python | C/C++ |
| --- | --- | --- |
| Functions and classes | `ast` from the standard library | lizard, a Python package that finds C and C++ functions and their line ranges |
| Comments | `tokenize`, plus docstrings from `ast` | troy-check's own scanner for `//` and `/* */` comments |
| Doc comment | The docstring | A `///` or `/** */` block directly above the declaration (D21) |

## 7. Module dependencies (R07)

The module map comes from the table in section 3 of `docs/architecture.md`, with columns Module, Owns, External interfaces, and May depend on (D19):

- **Owns** and **External interfaces** list path patterns in backticks, for example `` `src/app/storage/**` `` and `` `src/app/storage/__init__.py` ``.
- **May depend on** lists module names, or None.

The F01 architecture template's guidance for section 3 changes to ask for this.

Imports are read per language:

- **Python.** `import` and `from ... import` statements, read with `ast` and resolved to repository files through `[lang] source_roots`, for example `["src"]`. Imports that resolve to no repository file are third-party and ignored.
- **C/C++.** `#include "..."` lines, resolved against the including file's folder and `[lang] include_dirs`. `#include <...>` is external and ignored.

For each import in a changed file whose target lies in another module:

1. The importer's module lists the target module under May depend on. Otherwise R07 fails.
2. The target file matches the target module's External interfaces. Otherwise R07 fails, because the import reaches into the module's internals.

R07 also fails when the declared May depend on graph has a cycle, or when the imports of the whole repository form a cycle between modules that includes an import from a changed file. Files that belong to no module, such as tests and scripts, are not checked.

## 8. Python pack

### 8.1 Environment (D20)

Following the Python environment rule in requirements section 8 and the setup in troy-voice:

- **Series.** Projects that will run together on one platform form a series. They share one mamba environment, named after the series, like troy-voice's `troy-agent-env`. A project in no series is a series of one, with an environment named after itself. Sharing makes a version conflict show up as soon as a second project needs the package, not when the platform first loads them all.
- `.troy-mode/config.toml` names the environment and lists the members as folders on Troy's PC:

```toml
[lang]
environment = "troy-agent-env"
series = ["../troy-voice", "."]
```

- `environment.yml` is the same file in every member. mamba provides only Python and uv:

```yaml
name: <environment>
channels:
  - conda-forge
dependencies:
  - python=3.13
  - uv
```

- **One lock per series.** `requirements-dev.lock` pins every package of every member, so all members install exactly the same versions. It is compiled from all members' `pyproject.toml` files together, and the same file is committed in every member:

```text
uv pip compile ../troy-voice/pyproject.toml ./pyproject.toml --extra dev --universal -o requirements-dev.lock
```

- Setup on Troy's PC. The first two lines run once per series, the rest once per member:

```text
mamba env create -f environment.yml
mamba activate <environment>
uv pip install -r requirements-dev.lock
uv pip install -e . --no-deps
```

- CI installs from the member's own copy of the lock, so it needs no other member.
- Outside an activated shell, commands run as `mamba run -n <environment> <command>`.
- No `.venv` folder is ever created.
- A shared environment has a cost: one member's upgrade reaches every member at once. So after a lock change, every member's tests run in the shared environment before the change merges, and the other members get the new lock in their own PRs. Automating this belongs to F07.

### 8.2 Tools (D24)

The `pyproject.toml` fragment adds a `dev` extra with ruff, mypy, pytest, and coverage, and configures them:

- **ruff** lints with troy-voice's rule set plus the `D` rules, with `convention = "google"`, which checks docstring format (R05). It also checks formatting.
- **mypy** runs in strict mode, as in troy-voice.
- **pytest** finds tests in `tests/`, with `addopts = "-ra --strict-markers"`.
- **coverage** measures branches: `branch = true`, `source = ["src"]`.

### 8.3 Commands

| Step | Command |
| --- | --- |
| Lint and format | `ruff check` and `ruff format --check` |
| Types | `mypy` |
| Tests | `coverage run -m pytest --junitxml=reports/junit.xml`. Its exit code is ignored, because troy-check decides which failures are allowed. |
| Coverage report | `coverage xml -o reports/coverage.xml` |
| Rules | `python .troy-mode/checks/troy_check.py code --base <ref> --title <title> --junit reports/junit.xml --coverage reports/coverage.xml` |

### 8.4 Config fragment

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

### 8.5 CI job

`workflow-job.yml` adds a job, `troy-mode code checks`, to the project workflow from F02. It checks out the full history, creates the environment with `mamba-org/setup-micromamba` pinned to a commit SHA, installs from the lock file, and runs the steps in section 8.3 with the PR's base, head, title, and description.

## 9. C/C++ pack

### 9.1 Toolchain (D22)

- CMake 3.28 or newer with Ninja. C++20 and C17.
- GoogleTest 1.18.0, built from its release archive with the project's own compiler (D25), and run through CTest.
- The checks and coverage use GCC with gcov. gcovr writes the Cobertura XML.
- In CI, the GCC that ships with Ubuntu. On Troy's PC, the MSYS2 GCC 15 that is already on the PATH, so the same checks run locally.
- Visual Studio 2026 (MSVC) stays available through a separate CMake preset, `msvc`, for building and debugging. That preset measures no coverage.

### 9.2 Environment

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
```

mamba provides the non-Python tools, with clang-format and clang-tools pinned to one major version, so CI and Troy's PC format code the same way. uv installs the Python tools, gcovr and lizard, from `requirements-tools.lock`, which is compiled from `requirements-tools.in`. The compiler comes from outside the environment, as section 9.1 says, and so does GoogleTest (D25). Series, the shared environment, and the series lock work as in section 8.1.

### 9.3 Doc comments and format (D21)

- Every function and class declaration has a `///` (or `/** */`) comment directly above it. The content follows Google's C++ style: what it does, its parameters, return value, and errors, in full sentences.
- Doxygen checks that they exist. The pack's `Doxyfile` sets `WARN_IF_UNDOCUMENTED = YES`, `EXTRACT_PRIVATE = YES`, `EXTRACT_STATIC = YES`, and `EXTRACT_ANON_NSPACES = YES`. troy-check reads the warning log and keeps warnings on changed lines (R05).
- clang-format with `BasedOnStyle: Google` checks the format of changed files.
- clang-tidy runs a small set of bug-finding checks (`bugprone-*`, `performance-*`). The exact list is the Developer's choice, recorded in `.clang-tidy`.

### 9.4 Commands

| Step | Command |
| --- | --- |
| Configure and build | `cmake --preset coverage` and `cmake --build --preset coverage` |
| Format and lint | `clang-format --dry-run --Werror` and `clang-tidy` on changed files |
| Tests | `ctest --preset coverage --output-junit reports/junit.xml`. Its exit code is ignored. |
| Coverage report | `gcovr --cobertura reports/coverage.xml` |
| Doc comments | `doxygen .troy-mode/lang/cpp/Doxyfile`, writing `reports/doxygen.log` |
| Rules | `python .troy-mode/checks/troy_check.py code ... --junit reports/junit.xml --coverage reports/coverage.xml --doc-warnings reports/doxygen.log` |

### 9.5 Config fragment

```toml
[lang]
name = "cpp"
include_dirs = ["include", "src"]

[paths]
tests = ["**/*_test.cc", "**/*_test.cpp"]
dependencies = ["CMakeLists.txt", "**/CMakeLists.txt", "cmake/**", "CMakePresets.json",
                "environment.yml", "requirements*.lock"]
lock = ["requirements*.lock"]
```

CMake files count as dependencies, because adding a library happens there. Dependency files may change in source and test PRs (F02 design D9).

### 9.6 CI job

Like section 8.5, plus a configure and build step. Linux only.

## 10. How F03 is built and tested

F03 lands in four PRs, each with one commit and its tests written first (D15):

1. **Engine, tests and coverage.** R09, R10, R11, the `code` subcommand, and R01's subject check. The tests use small hand-written JUnit and Cobertura files.
2. **Engine, code shape.** R04 to R07 with the Python adapter.
3. **Python pack.** The files in section 8, plus a small sample Python project that CI takes through the whole pack: environment, tests, coverage, and `troy-check code`.
4. **C/C++ pack.** The C/C++ adapter and the files in section 9, plus a small sample C++ project that CI takes through the pack.

troy-pstack's CI runs the unit tests on Linux and Windows and the sample projects on Linux. On Troy's PC, troy-pstack's own environment, `troy-pstack`, runs them (D26).

F03's status becomes "Written" when PR 4 merges. It becomes "Runs on a sample project" once both sample projects pass in CI.

## 11. Not in F03

- The TypeScript/JavaScript pack. It comes later, in the same shape.
- Copying a pack into a project and choosing the language (F06).
- Performance tests. R14 is a review rule, and they run at version release (Q7).
- Role instructions that tell the Test Engineer how to name tests and the Developer how to write mocks (F04).
- Updating the lock in every member of a series after a dependency change, and rerunning every member's tests in the shared environment (F07).

## 12. Decisions for Troy

Troy approved all ten proposals on 2026-11-05, D20 after one revision. During part 4, on 2026-11-06, Troy chose D25 and D26.

| ID | Decision | Proposal |
| --- | --- | --- |
| D15 | How F03 is shaped and delivered. | A language-independent engine plus thin language packs, as in section 1. F03 takes R09, which no feature lists. It lands in four PRs (section 10), an exception to Q10's one PR per feature, because one PR would hold two packs and the whole engine. |
| D16 | How tests carry their IDs (R10). | The test's own name starts with its case ID or bug ID (section 4.1). Names reach troy-check through JUnit XML in every language. Framework markers would need a different reader for each language. |
| D17 | How troy-check knows which features are accepted and which bugs are fixed. | From the base's history: `[F04 6/6 accept]` and `[B12 B/B fix]` commit subjects. R01 also requires the commit subject to equal the PR title. This works offline and needs no GitHub call. |
| D18 | How R11 measures changed-line coverage. | troy-check reads Cobertura XML itself, so no third-party tool such as diff-cover is needed. An exclusion comment needs a `reason:` on the same line. |
| D19 | Where the module map for R07 comes from, and which tool checks it. | The module table in `docs/architecture.md` section 3, so the architecture stays the single source. troy-check's own checker for both languages, in place of import-linter for Python. The architecture template asks for path patterns in the Owns and External interfaces columns. |
| D20 | The Python environment. troy-voice shares one environment, `troy-agent-env`, across projects, and has no lock file. | Revised after Troy's answer on 2026-11-05. Troy approved the lock file and wants projects in one series to share one environment, so a platform built from them has no version conflicts. So: one environment per series, and one `requirements-dev.lock` per series, compiled from every member's `pyproject.toml` and committed in each member (section 8.1). Per-project locks in a shared environment would let members pin different versions of the same package. Troy approved the revision the same day. |
| D21 | C/C++ doc comments. Google's C++ style uses plain `//` comments, which no tool can tell apart from other comments. | `///` comments with Google-style content, so Doxygen can report what is undocumented. |
| D22 | The C/C++ compiler for the checks. | GCC with gcov everywhere, because coverage needs it: Ubuntu's GCC in CI, MSYS2 GCC 15 on your PC. MSVC through Visual Studio 2026 stays available for building and debugging, without coverage. |
| D23 | What "comments in English only" (R05) means to a script. | No Chinese, Japanese, or Korean characters in comments and doc comments: CJK ideographs, kana, Hangul, and CJK and fullwidth punctuation. Other non-ASCII text, such as names with accents and symbols like →, is allowed. |
| D24 | Python tools beyond the R rules. | The pack carries troy-voice's defaults: the broad ruff rule set, ruff's format check, and mypy in strict mode. A project can drop them through the rule change flow. |
| D25 | Where GoogleTest comes from. Section 9.2 put it in the mamba environment, but conda-forge's GoogleTest for Windows is built with MSVC, and MSYS2 GCC cannot link it. This was tried on Troy's PC. | `cmake/troy.cmake` downloads the GoogleTest 1.18.0 release archive with CMake's FetchContent, checks its SHA256, and builds it with the project's own compiler. CI and Troy's PC use the same version. Troy chose this on 2026-11-06, over the platforms' package managers and over MSVC on Troy's PC. |
| D26 | Where troy-pstack's own tests get lizard, which the C/C++ adapter needs. They used to run with the system Python. | troy-pstack is a series of one with its own environment, `troy-pstack`, created from `troy-mode/dev/environment.yml`, with lizard and gcovr from `troy-mode/dev/requirements-dev.lock`. The environment also holds the C/C++ tools, so the C++ sample runs on Troy's PC. CI installs the same lock. Troy chose this on 2026-11-06. |

Requirements 1.6 records the approved changes:

- The F03 row adds R09, the engine and packs, and the four PRs (D15).
- R01 adds the subject check (D17). R10 says how tests carry IDs (D16). The rules template follows.
- Section 8's Python environment rule adds series, one environment per series, and one lock per series (D20).

The architecture template's section 3 guidance changes with requirements 1.6 (D19).

## 13. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-05 | First draft. |
| 0.2 | 2026-11-05 | Troy approved D15 to D24 except D20. D20 is revised: one environment and one lock per series (section 8.1). |
| 1.0 | 2026-11-05 | Approved by Troy with D15 to D24, D20 as revised. |
| 1.1 | 2026-11-06 | D25 and D26, which Troy chose during part 4. GoogleTest leaves the environment (sections 9.1 and 9.2), clang-format and clang-tools are pinned to version 23, and section 2 lists the samples and troy-pstack's own environment. |
