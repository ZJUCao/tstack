# troy-mode Python pack

| | |
| --- | --- |
| Version | 1.0 |
| Date | 2026-11-06 |
| Source of truth | This English file. [`README.zh-CN.md`](README.zh-CN.md) is the Chinese mirror. |

The Python pack makes troy-check's language rules run in a Python project: R04 to R07 on the code, and R09 to R11 on the test run. `troy-init` (F06) copies it into a project. [The F03 design](../../../docs/troy-mode/design/F03-language-packs.md), section 8, records why each choice was made.

## 1. Files

| File | Where it lands in the project | What it holds |
| --- | --- | --- |
| [`environment.yml`](environment.yml) | `environment.yml` | The series environment: Python 3.13 and uv from conda-forge. `troy-init` fills in `{{environment}}`. |
| [`pyproject.toml`](pyproject.toml) | Added at the end of `pyproject.toml` | The `dev` extra (coverage, mypy, pytest, ruff) and the settings of those tools. |
| [`config.toml`](config.toml) | Added to `.troy-mode/config.toml` | `[lang]` and the Python path patterns. |
| [`workflow-job.yml`](workflow-job.yml) | Added under `jobs:` in `.github/workflows/troy-mode.yml` | The `troy-mode code checks` job. |

The project also commits `requirements-dev.lock` (section 2), and its `.gitignore` lists `reports/`, `.coverage`, and the caches of mypy, pytest, and ruff.

## 2. Environment

Projects that will run together on one platform form a series, and share one mamba environment named after the series. A project in no series is a series of one. mamba provides only Python and uv. uv installs every package from `requirements-dev.lock`, which every member of the series commits. No `.venv` folder is ever created.

The lock is compiled from every member's `pyproject.toml` together. For a series of one:

```text
uv pip compile pyproject.toml --extra dev --universal -o requirements-dev.lock
```

Setup on Troy's PC. The first two lines run once per series, the rest once per member:

```text
mamba env create -f environment.yml
mamba activate <environment>
uv pip install -r requirements-dev.lock
uv pip install -e . --no-deps
```

## 3. Commands

Run them in the activated environment, or as `mamba run -n <environment> <command>`.

| Step | Command |
| --- | --- |
| Lint and format | `ruff check` and `ruff format --check` |
| Types | `mypy` |
| Tests | `coverage run -m pytest --junitxml=reports/junit.xml`. Failing tests do not stop the job: troy-check decides which failures are allowed. |
| Coverage report | `coverage xml -o reports/coverage.xml` |
| Rules | `python .troy-mode/checks/troy_check.py code --base <ref> --title <title> --junit reports/junit.xml --coverage reports/coverage.xml` |

## 4. Tool settings

- **ruff** uses troy-voice's rule set plus the `D` rules with the Google convention, which check docstrings (R05). It skips `.troy-mode`, because troy-check is checked in troy-pstack. It ignores RUF001, so strings may hold Chinese punctuation. RUF002 and RUF003 stay on, because R05 keeps Chinese out of docstrings and comments anyway. Tests may use `assert` and need no annotations.
- **mypy** checks `src` in strict mode.
- **pytest** finds tests in `tests/` and runs with `-ra --strict-markers`.
- **coverage** measures lines and branches in `src`.

A project adds its own settings, such as troy-voice's banned time functions, after the pack's tables. Dropping one of the pack's settings goes through the rule change flow.

## 5. CI job

The job checks out the PR with its full history, creates the environment with `mamba-org/setup-micromamba` pinned to a commit, installs from the lock, and runs the steps of section 3. As in the troy-check job from F02, the PR's title and description reach the shell only through environment variables, and troy-check runs from the base commit when it exists there, so a PR cannot change the code that judges it.

## 6. Sample project

[`troy-mode/samples/python`](../../samples/python) holds textstats, a small project whose feature F01 goes through design, test plan, mock, tests, and implementation. [`build_sample.py`](../../dev/build_sample.py) builds its git repository the way `troy-init` sets up a project. troy-pstack's workflow `troy-python-sample.yml` then runs the steps of section 5 on two PRs:

- the tests PR, where every new test must fail against the mock (R09);
- the implementation PR, where every test passes and the changed lines are covered (R11).

`troy-mode/dev/tests/test_python_pack.py` checks that the sample's workflow runs the same steps as `workflow-job.yml`. To build the sample yourself:

```text
python troy-mode/dev/build_sample.py build python --pr impl --out <empty folder>
```
