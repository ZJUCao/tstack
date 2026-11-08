"""Shared fixtures for the F07 engine tests (F07 design 14.1).

Each test builds a seed repository whose ``main`` holds the state of
``origin/main`` the test needs, makes ``origin`` from it with
``git clone --bare``, clones ``origin``, and works on a branch of the clone,
so no test pushes ``main``. A fake ``gh``, first on the ``PATH``, serves open
PRs and their comments from a JSON file and records each call. A fake
``mamba`` beside it records calls too, and no test expects one. The engine,
``troy-mode/flow/troy_flow.py``, runs as a subprocess with
``sys.executable``. Nothing here imports it.
"""

from __future__ import annotations

import atexit
import itertools
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence, Union

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
ENGINE = PLUGIN_ROOT / "troy-mode/flow/troy_flow.py"
CHECKS_SOURCE = PLUGIN_ROOT / "troy-mode/checks"
EMAIL = "148482542+ZJUCao@users.noreply.github.com"
LOGIN = "ZJUCao"
DATE = "2026-11-07"
PROJECT = "wordcount"
WORK_BRANCH = "troy-mode/work"
ENVIRONMENT = "wordcount"

CONFIG = ".troy-mode/config.toml"
RECORD = ".troy-mode/install.toml"
PROGRESS = ".troy-mode/progress.md"
REQUIREMENTS = "docs/requirements.md"
REQUIREMENTS_ZH = "docs/requirements.zh-CN.md"
ARCHITECTURE = "docs/architecture.md"
ARCHITECTURE_ZH = "docs/architecture.zh-CN.md"
RULES = "docs/rules.md"
GITIGNORE = ".troy-mode/progress.md\nreports/\n__pycache__/\n"
SETUP_TITLE = "[rules] Set up troy-mode"
STAGE_NAMES = {1: "design", 2: "test-plan", 3: "mock", 4: "tests", 5: "impl", 6: "accept"}
STAGE_TASKS = {1: "IF1", 2: "TM1", 3: "DV1", 4: "TE1", 5: "DV2", 6: "PM3"}
NEXT_KEYS = ("action", "item", "stage", "task", "title", "branch", "pr", "merged_by", "doc",
             "rounds", "attempts")
PROGRESS_FIELDS = ("Current version", "Current feature", "Stage", "Open PRs", "Waiting on Troy",
                   "Open issues", "Next action", "Last updated")
ANY = object()

_DROPPED_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_COMMON_DIR", "GIT_CEILING_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_COUNT",
                "GIT_CONFIG_PARAMETERS", "PYTHONUTF8", "PYTHONIOENCODING", "CLAUDE_PLUGIN_ROOT",
                "GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "MAMBA_EXE", "TROY_MODE_ENV_PREFIX",
                "GH_TOKEN", "GITHUB_TOKEN", "GH_HOST", "GH_REPO")

_SCRATCH = tempfile.TemporaryDirectory(prefix="troyflow-", ignore_cleanup_errors=True)
atexit.register(_SCRATCH.cleanup)
SCRATCH = Path(_SCRATCH.name)
_GLOBAL_CONFIG = SCRATCH / "gitconfig"
_GLOBAL_CONFIG.write_text("[maintenance]\n\tauto = false\n[gc]\n\tauto = 0\n", encoding="utf-8")
_COUNTER = itertools.count(1)
_ORIGINS: dict = {}
Content = Union[str, bytes, None]


# ------------------------------------------------------------------ basics

def new_dir(prefix: str) -> Path:
    """Creates a new empty folder in the scratch area.

    Args:
        prefix: The start of the folder's name.

    Returns:
        The new folder.
    """
    path = SCRATCH / f"{prefix}{next(_COUNTER)}"
    path.mkdir()
    return path


def base_env(extra: Optional[Mapping[str, str]] = None) -> dict:
    """Builds an environment that isolates git from the machine's config.

    Args:
        extra: Variables that override or extend the isolated defaults.

    Returns:
        A new environment for a subprocess.
    """
    env = {k: v for k, v in os.environ.items() if k not in _DROPPED_ENV}
    env.update({
        "GIT_CONFIG_GLOBAL": str(_GLOBAL_CONFIG), "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": EMAIL,
        "GIT_COMMITTER_NAME": "Test Committer", "GIT_COMMITTER_EMAIL": EMAIL,
        "GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1",
    })
    env.update(extra or {})
    return env


def git_proc(cwd: Path, *args: str, input_bytes: Optional[bytes] = None
             ) -> subprocess.CompletedProcess:
    """Runs git and returns the finished process, whatever its exit code.

    Args:
        cwd: The folder to run in.
        *args: The arguments after ``git``.
        input_bytes: Bytes for standard input, or None for none.

    Returns:
        The finished process, with text output.
    """
    proc = subprocess.run(["git", *args], cwd=str(cwd), env=base_env(), capture_output=True,
                          input=input_bytes, stdin=None if input_bytes is not None
                          else subprocess.DEVNULL, check=False)
    return subprocess.CompletedProcess(proc.args, proc.returncode,
                                       proc.stdout.decode("utf-8", "replace"),
                                       proc.stderr.decode("utf-8", "replace"))


def git(cwd: Path, *args: str, input_bytes: Optional[bytes] = None) -> str:
    """Runs git, raises when it fails, and returns its standard output.

    Args:
        cwd: The folder to run in.
        *args: The arguments after ``git``.
        input_bytes: Bytes for standard input, or None for none.

    Returns:
        The standard output.

    Raises:
        RuntimeError: git exited with a code other than 0.
    """
    proc = git_proc(cwd, *args, input_bytes=input_bytes)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {proc.stderr}")
    return proc.stdout


def as_bytes(content: Union[str, bytes]) -> bytes:
    """Encodes text as UTF-8 and returns bytes unchanged.

    Args:
        content: Text or bytes.

    Returns:
        The bytes.
    """
    return content if isinstance(content, bytes) else content.encode("utf-8")


def write_file(root: Path, rel: str, content: Union[str, bytes]) -> None:
    """Writes a file with the exact bytes given (LF for text), creating folders.

    Args:
        root: The folder the path is relative to.
        rel: The path, with ``/``.
        content: Text, written as UTF-8 without newline translation, or bytes.
    """
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(as_bytes(content))


def lf(data: bytes) -> bytes:
    """Replaces CRLF with LF.

    Args:
        data: The bytes.

    Returns:
        The bytes with LF line endings.
    """
    return data.replace(b"\r\n", b"\n")


def crlf(text: str) -> bytes:
    """Encodes text as UTF-8 with CRLF line endings.

    Args:
        text: Text with LF line endings.

    Returns:
        The CRLF bytes.
    """
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def same_path(first, second) -> bool:
    """Whether two paths name the same place, existing or not.

    Args:
        first: A path.
        second: Another path.

    Returns:
        True when both resolve to the same normalized path.
    """
    def norm(path) -> str:
        """Normalizes one path for comparison."""
        return os.path.normcase(os.path.realpath(os.path.abspath(str(path))))
    return norm(first) == norm(second)


def parallel(func: Callable, items: Iterable, workers: int = 8) -> list:
    """Applies a function to every item in a thread pool, keeping the items' order.

    Each call starts its own processes, so independent engine runs finish
    sooner side by side. Only use it for calls that share no clone they change.

    Args:
        func: A function of one argument.
        items: The arguments.
        workers: The most calls at a time.

    Returns:
        The results, in the order of the items.
    """
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(func, items))


def slug(name: str) -> str:
    """A feature folder's slug: lower case, other characters made single dashes.

    Args:
        name: The feature's name.

    Returns:
        For example ``count-words`` for ``Count words``.
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ---------------------------------------------------------------- documents

@dataclass(frozen=True)
class Feature:
    """One row of the requirements' features table.

    Attributes:
        id: The feature ID, for example ``F01``.
        name: The Feature cell.
        hard: Hard dependency IDs.
        soft: Soft dependency IDs.
        version: The Version cell.
        status: The Status cell.
    """

    id: str
    name: str
    hard: tuple = ()
    soft: tuple = ()
    version: str = "v0.1"
    status: str = "Not started"

    @property
    def folder(self) -> str:
        """The feature's folder, for example ``docs/features/F01-count-words``."""
        return f"docs/features/{self.id}-{slug(self.name)}"

    @property
    def design(self) -> str:
        """The path of the feature's English design."""
        return f"{self.folder}/design.md"

    @property
    def plan(self) -> str:
        """The path of the feature's English test plan."""
        return f"{self.folder}/test-plan.md"

    def title(self, stage: int) -> str:
        """The PR title of one stage, for example ``[F01 3/6 mock] Count words``."""
        return f"[{self.id} {stage}/6 {STAGE_NAMES[stage]}] {self.name}"

    def branch(self, stage: int) -> str:
        """The branch of one stage, for example ``troy-mode/f01-3-mock``."""
        return f"troy-mode/{self.id.lower()}-{stage}-{STAGE_NAMES[stage]}"


F01 = Feature("F01", "Count words")
F02 = Feature("F02", "Count lines", hard=("F01",))
F03 = Feature("F03", "Count characters", soft=("F01",))
F04 = Feature("F04", "Report totals", hard=("F02",))
F05 = Feature("F05", "Watch folders")
TWO = (F01, F02)
FIVE = (F01, F02, F03, F04, F05)


def front_matter(doc_id: str, lang: str, version: str, mirror: str,
                 status: Optional[str] = None, updated: str = "2026-11-01") -> str:
    """A document's YAML front matter (F01 design 4).

    Args:
        doc_id: The ``troy-doc`` value.
        lang: ``en`` or ``zh-CN``.
        version: The ``version`` value.
        mirror: The partner's file name (``mirror`` or ``mirror-of``).
        status: The ``status`` value, or None for a draft status.
        updated: The ``updated`` value.

    Returns:
        The front matter with its two ``---`` lines and a blank line after.
    """
    english = lang == "en"
    if status is None:
        status = "Draft. In review." if english else "草稿，审查中。"
    key = "mirror" if english else "mirror-of"
    return (f'---\ntroy-doc: "{doc_id}"\nlang: "{lang}"\nversion: "{version}"\n'
            f'updated: "{updated}"\nstatus: "{status}"\n{key}: "{mirror}"\n---\n\n')


def requirements_text(features: Sequence[Feature] = TWO, order: Optional[Sequence[str]] = None,
                      version: str = "1.0", order_line: bool = True) -> str:
    """The English requirements with a features table and an order line.

    Args:
        features: The table's rows, in table order.
        order: The IDs of the order line, or None for the table order.
        version: The front matter's version.
        order_line: Whether the document has a "Topological order:" line.

    Returns:
        The document text.
    """
    rows = []
    for item in features:
        hard = ", ".join(item.hard) or "None"
        soft = ", ".join(item.soft) or "None"
        rows.append(f"| {item.id} | {item.name} | {hard} | {soft} | {item.version} "
                    f"| {item.status} |")
    ids = list(order) if order is not None else [item.id for item in features]
    line = f"Topological order: {', '.join(ids)}\n" if order_line else "No order yet.\n"
    versions = sorted({item.version for item in features})
    plan = "".join(f"| {v} | {', '.join(i.id for i in features if i.version == v)} |\n"
                   for v in versions)
    return (front_matter("requirements", "en", version, "requirements.zh-CN.md")
            + f"# {PROJECT} requirements\n\n## 1. Goal\n\nCount words in text files.\n\n"
            "## 4. Features\n\n"
            "| ID | Feature | Hard dependencies | Soft dependencies | Version | Status |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n\n"
            "## 5. Dependency graph and order\n\n" + line + "\n"
            "## 6. Version plan\n\n| Version | Features |\n| --- | --- |\n" + plan)


def requirements_zh(version: str = "1.0") -> str:
    """The Chinese mirror of the requirements (the engine reads the English file only).

    Args:
        version: The front matter's version.

    Returns:
        The document text.
    """
    return (front_matter("requirements", "zh-CN", version, "requirements.md")
            + f"# {PROJECT} 需求\n\n## 1. 目标\n\n统计文本文件中的单词数。\n")


def architecture_text(version: str = "1.0", lang: str = "en") -> str:
    """The architecture document or its mirror.

    Args:
        version: The front matter's version.
        lang: ``en`` or ``zh-CN``.

    Returns:
        The document text.
    """
    mirror = "architecture.zh-CN.md" if lang == "en" else "architecture.md"
    body = "One module, `src/wordcount/**`.\n" if lang == "en" else "一个模块。\n"
    return front_matter("architecture", lang, version, mirror) + f"# {PROJECT}\n\n{body}"


def design_text(feature: Feature, version: str = "1.0", lang: str = "en") -> str:
    """A feature design in the shape of F01's ``feature-design`` template.

    Section 2 holds a fenced block with a line that starts ``## 4.``, which
    is not a heading, so a section check must skip fenced code blocks.

    Args:
        feature: The feature.
        version: The front matter's version.
        lang: ``en`` or ``zh-CN``.

    Returns:
        The document text.
    """
    english = lang == "en"
    mirror = "design.zh-CN.md" if english else "design.md"
    head = front_matter(f"{feature.id}-design", lang, version, mirror)
    if english:
        return head + (
            f"# {feature.id} {feature.name}: interface design\n\n"
            f"## 1. Feature\n\n- ID and name: {feature.id} {feature.name}\n"
            "- Hard dependencies: None\n- Soft dependencies: None\n\n"
            "## 2. Interfaces\n\n### 2.1 `count`\n\n- Module: wordcount\n\n"
            "```python\ndef count(text: str) -> int\n```\n\n"
            "A heading inside a fenced block is text:\n\n"
            "```text\n## 4. Not a heading inside a fence\n```\n\n"
            "## 3. Changes to existing interfaces\n\nNone\n\n"
            "## 4. Architect review\n\n| Item | Result | Note |\n| --- | --- | --- |\n"
            "| Fits the module layout and the data model | Pass | None |\n\n"
            "| Round | Issue | Resolution |\n| --- | --- | --- |\n| 1 | None | None |\n\n"
            "## 5. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n"
            "| 0.1 | 2026-11-01 | First draft. |\n")
    return head + (
        f"# {feature.id} {feature.name}：接口设计\n\n"
        f"## 1. 功能\n\n- 编号和名称：{feature.id} {feature.name}\n\n"
        "## 2. 接口\n\n### 2.1 `count`\n\n"
        "```python\ndef count(text: str) -> int\n```\n\n"
        "```text\n## 4. 围栏里的文字不是标题\n```\n\n"
        "## 3. 对已有接口的修改\n\n无\n\n"
        "## 4. 架构师审查\n\n| 项目 | 结果 | 备注 |\n| --- | --- | --- |\n"
        "| 符合模块划分和数据模型 | Pass | 无 |\n\n"
        "| 轮次 | 问题 | 解决方式 |\n| --- | --- | --- |\n| 1 | 无 | 无 |\n\n"
        "## 5. 修改记录\n\n| 版本 | 日期 | 修改 |\n| --- | --- | --- |\n"
        "| 0.1 | 2026-11-01 | 初稿。 |\n")


def plan_text(feature: Feature, version: str = "1.0", lang: str = "en") -> str:
    """A feature test plan or its mirror.

    Args:
        feature: The feature.
        version: The front matter's version.
        lang: ``en`` or ``zh-CN``.

    Returns:
        The document text.
    """
    mirror = "test-plan.zh-CN.md" if lang == "en" else "test-plan.md"
    head = front_matter(f"{feature.id}-test-plan", lang, version, mirror)
    case = f"{feature.id}-T01"
    if lang == "en":
        return head + f"# {feature.id} test plan\n\n## 1. Unit tests\n\n- {case}: counts.\n"
    return head + f"# {feature.id} 测试计划\n\n## 1. 单元测试\n\n- {case}：计数。\n"


def rules_text() -> str:
    """A minimal rules table."""
    return (front_matter("rules", "en", "1.0", "rules.zh-CN.md")
            + "# Rules\n\n| ID | Rule |\n| --- | --- |\n| R01 | One commit per PR. |\n")


def config_text(lang: Optional[str] = "python", extra: str = "", mode: str = "strict",
                environment: str = ENVIRONMENT) -> str:
    """A project config that troy-check accepts.

    Args:
        lang: ``python``, ``cpp``, or None for no ``[lang]`` table.
        extra: Raw TOML appended at the end, for example ``[flow]``.
        mode: The ``[attribution]`` mode.
        environment: The ``[lang] environment`` value.

    Returns:
        The TOML text.
    """
    text = (f'[identity]\ncommit_email = "{EMAIL}"\n\n'
            '[paths]\ndependencies = ["pyproject.toml"]\n\n'
            f'[attribution]\nmode = "{mode}"\n')
    if lang == "python":
        text += (f'\n[lang]\nname = "python"\nsource_roots = ["src"]\n'
                 f'environment = "{environment}"\nseries = ["."]\n')
    elif lang == "cpp":
        text += (f'\n[lang]\nname = "cpp"\ninclude_dirs = ["include", "src"]\n'
                 f'environment = "{environment}"\nseries = ["."]\n')
    return text + (("\n" + extra) if extra else "")


def install_text(lang: Optional[str] = "python") -> str:
    """The install record (``.troy-mode/install.toml``) of the interface note.

    Args:
        lang: The pack's name, or None when the language step has not run.

    Returns:
        The TOML text.
    """
    text = f'[plugin]\nversion = "0.1.0"\n\n[steps]\nsetup = "{DATE}"\n'
    if lang:
        text += f'lang = "{DATE}"\n\n[lang]\nname = "{lang}"\n'
    return text


def base_files(features: Sequence[Feature] = TWO, lang: Optional[str] = "python",
               config_extra: str = "", requirements: Optional[str] = "1.0",
               architecture: Optional[str] = "1.0", installed: bool = True,
               order: Optional[Sequence[str]] = None, order_line: bool = True,
               mode: str = "strict", extra: Optional[Mapping[str, Content]] = None) -> dict:
    """The files of a troy-mode project's first commit on ``origin/main``.

    Args:
        features: The requirements' feature rows.
        lang: The pack in the config and the install record, or None.
        config_extra: Raw TOML appended to the config.
        requirements: The requirements' version, or None for no document.
        architecture: The architecture's version, or None for no document.
        installed: Whether ``.troy-mode/install.toml`` exists.
        order: The order line's IDs, or None for the table order.
        order_line: Whether the requirements have an order line.
        mode: The ``[attribution]`` mode.
        extra: More files, which replace the defaults of the same path.

    Returns:
        Paths mapped to their content.
    """
    files: dict = {
        "README.md": f"# {PROJECT}\n",
        ".gitignore": GITIGNORE,
        CONFIG: config_text(lang, config_extra, mode),
        RULES: rules_text(),
        "pyproject.toml": f'[project]\nname = "{PROJECT}"\nversion = "0.1.0"\n',
        "src/wordcount/__init__.py": '"""Counts words."""\n',
    }
    if installed:
        files[RECORD] = install_text(lang)
    if requirements is not None:
        files[REQUIREMENTS] = requirements_text(features, order, requirements, order_line)
        files[REQUIREMENTS_ZH] = requirements_zh(requirements)
    if architecture is not None:
        files[ARCHITECTURE] = architecture_text(architecture)
        files[ARCHITECTURE_ZH] = architecture_text(architecture, "zh-CN")
    files.update(extra or {})
    return files


def plugin_checks_files() -> dict:
    """The plugin's troy-check as a project copy: project path to bytes.

    Every file under ``troy-mode/checks/`` except the top-level ``tests/``,
    ``workflow.yml``, and ``config.default.toml``, and except ``__pycache__``
    folders and ``*.pyc`` files, mapped to ``.troy-mode/checks/<same path>``
    (interface note, the ``checks`` key).

    Returns:
        Paths mapped to the plugin's bytes.
    """
    files = {}
    for path in sorted(CHECKS_SOURCE.rglob("*")):
        rel = path.relative_to(CHECKS_SOURCE)
        if not path.is_file() or rel.parts[0] == "tests" or "__pycache__" in rel.parts:
            continue
        if rel.as_posix() in ("workflow.yml", "config.default.toml") or path.suffix == ".pyc":
            continue
        files[f".troy-mode/checks/{rel.as_posix()}"] = path.read_bytes()
    return files


# ------------------------------------------------------------------ history

@dataclass(frozen=True)
class Step:
    """One change to ``main`` in a seed repository.

    Attributes:
        subject: The commit's message (one line).
        files: ``(path, content)`` pairs; None content deletes the path.
        merge: For a PR merged with a merge commit, the merge commit's
            message. The commit with ``subject`` and ``files`` is then made
            on a side branch and merged into ``main``. None for a plain commit.
    """

    subject: str
    files: tuple = ()
    merge: Optional[str] = None


def step(subject: str, files: Optional[Mapping[str, Content]] = None,
         merge: Optional[str] = None) -> Step:
    """Builds a Step from a mapping of paths to content.

    Args:
        subject: The commit's subject.
        files: Paths mapped to content, None to delete.
        merge: The merge commit's message, or None for a plain commit.

    Returns:
        The step.
    """
    return Step(subject, tuple(sorted((files or {}).items())), merge)


def base_step(files: Optional[Mapping[str, Content]] = None, subject: str = SETUP_TITLE) -> Step:
    """The first commit of a project, holding its base files.

    Args:
        files: The files, or None for ``base_files()``.
        subject: The commit's subject.

    Returns:
        The step.
    """
    return step(subject, base_files() if files is None else files)


def stage_files(feature: Feature, stage: int, design: str = "1.0", plan: str = "1.0") -> dict:
    """The files one stage of the feature loop adds or changes.

    Args:
        feature: The feature.
        stage: The stage number, 1 to 6.
        design: The design's version (stage 1).
        plan: The test plan's version (stage 2).

    Returns:
        Paths mapped to content.
    """
    low = feature.id.lower()
    if stage == 1:
        return {feature.design: design_text(feature, design),
                f"{feature.folder}/design.zh-CN.md": design_text(feature, design, "zh-CN")}
    if stage == 2:
        return {feature.plan: plan_text(feature, plan),
                f"{feature.folder}/test-plan.zh-CN.md": plan_text(feature, plan, "zh-CN")}
    if stage == 3:
        return {f"src/wordcount/{low}.py":
                '"""Mock."""\n\n\ndef count(text: str) -> int:\n'
                '    """Counts."""\n    raise NotImplementedError\n'}
    if stage == 4:
        return {f"tests/test_{low}.py":
                f'"""Tests."""\n\n\ndef test_{low}_t01_counts():\n    """Counts."""\n'
                "    assert True\n"}
    if stage == 5:
        return {f"src/wordcount/{low}.py":
                '"""Impl."""\n\n\ndef count(text: str) -> int:\n'
                '    """Counts."""\n    return len(text.split())\n'}
    return {f"{feature.folder}/acceptance.md": f"# {feature.id} accepted\n"}


def stage_step(feature: Feature, stage: int, style: str = "rebase", pr: Optional[int] = None,
               design: str = "1.0", plan: str = "1.0") -> Step:
    """One merged stage PR, as the merge method leaves it on ``main``.

    Args:
        feature: The feature.
        stage: The stage number, 1 to 6.
        style: ``rebase`` (the PR's commit as is), ``squash`` (subject with
            `` (#<pr>)``), or ``merge`` (the PR's commit plus a merge commit).
        pr: The PR number, or None for 40 plus the stage.
        design: The design's version (stage 1).
        plan: The test plan's version (stage 2).

    Returns:
        The step.
    """
    number = pr if pr is not None else 40 + stage
    subject = feature.title(stage)
    files = stage_files(feature, stage, design, plan)
    if style == "squash":
        return step(f"{subject} (#{number})", files)
    if style == "merge":
        return step(subject, files, merge=f"Merge pull request #{number} from "
                                         f"{LOGIN}/{feature.branch(stage)}")
    return step(subject, files)


def stages(feature: Feature, upto: int, **kwargs) -> list:
    """The merged stages 1 to ``upto`` of a feature, as rebase merges.

    Args:
        feature: The feature.
        upto: The last merged stage, 0 to 6.
        **kwargs: Passed on to ``stage_step`` (``design``, ``plan``).

    Returns:
        A list of steps.
    """
    return [stage_step(feature, n, **kwargs) for n in range(1, upto + 1)]


# ------------------------------------------------------- part 2 history

CHANGE_PREFIX = "[docs] Change the requirements: "
RECORD_REQUIREMENTS = "[docs] Record Troy's approval of docs/requirements.md"
BUG_TAGS = {"test": "A/B test", "fix": "B/B fix", "test-fix": "test-fix"}


def bug_title(bug: str, kind: str, summary: str) -> str:
    """A bug PR's title (F02 design 4).

    Args:
        bug: The bug ID, for example ``B12``.
        kind: ``test`` (PR A), ``fix`` (PR B), or ``test-fix``.
        summary: The summary after the bracket.

    Returns:
        For example ``[B12 A/B test] Crash on empty history``.
    """
    return f"[{bug} {BUG_TAGS[kind]}] {summary}"


def bug_branch(bug: str, kind: str) -> str:
    """A bug PR's branch (design 11.1), for example ``troy-mode/b12-fix``."""
    return f"troy-mode/{bug.lower()}-{kind}"


def bug_step(bug: str, kind: str, summary: str, pr: Optional[int] = None) -> Step:
    """One merged bug PR, as a rebase (or, with ``pr``, a squash) leaves it on ``main``.

    Args:
        bug: The bug ID.
        kind: ``test``, ``fix``, or ``test-fix``.
        summary: The title's summary.
        pr: The PR number for a squash subject with `` (#<pr>)``, or None.

    Returns:
        The step.
    """
    low = bug.lower()
    if kind == "fix":
        files = {f"src/wordcount/fix_{low}.py": f'"""The fix of {bug}."""\n'}
    else:
        files = {f"tests/test_{low}.py":
                 f'"""Tests of {bug}."""\n\n\ndef test_{low}_empty_history():\n'
                 '    """Fails before the fix."""\n    assert True\n'}
    subject = bug_title(bug, kind, summary)
    return step(subject + (f" (#{pr})" if pr is not None else ""), files)


def rework(feature: Feature, change: str = "Count blank lines") -> Feature:
    """The feature with PM2's Status cell ``Needs rework (<change>)`` (design 11.2).

    Args:
        feature: The feature.
        change: The change named in the cell.

    Returns:
        A copy of the feature with the new Status cell.
    """
    return replace(feature, status=f"Needs rework ({change})")


def requirements_files(features: Sequence[Feature] = TWO, version: str = "2.0") -> dict:
    """Both requirements files at one version, for a commit that changes them.

    Args:
        features: The features table's rows.
        version: The front matter's version.

    Returns:
        Paths mapped to content.
    """
    return {REQUIREMENTS: requirements_text(features, version=version),
            REQUIREMENTS_ZH: requirements_zh(version)}


def change_step(summary: str = "Count blank lines", features: Sequence[Feature] = TWO,
                version: str = "2.0", pr: Optional[int] = None) -> Step:
    """A merged ``[docs] Change the requirements: <summary>`` PR (design 11.2).

    Args:
        summary: The change's summary.
        features: The features table after the change.
        version: The requirements' version after the change: a next major
            when Troy approved in chat (``approve``), a minor when he merged
            on GitHub.
        pr: The PR number for a squash subject, or None.

    Returns:
        The step.
    """
    subject = CHANGE_PREFIX + summary + (f" (#{pr})" if pr is not None else "")
    return step(subject, requirements_files(features, version))


def record_step(features: Sequence[Feature] = TWO, version: str = "2.0") -> Step:
    """A merged ``[docs] Record Troy's approval of docs/requirements.md`` PR.

    Args:
        features: The features table.
        version: The requirements' version after ``approve``.

    Returns:
        The step.
    """
    return step(RECORD_REQUIREMENTS, requirements_files(features, version))


def custom_design(feature: Feature, section2: Optional[str], section1_extra: str = "",
                  section3: str = "None\n", version: str = "1.0") -> str:
    """An English design whose section 2 the test chooses (design 11.2, the skipped mock).

    Args:
        feature: The feature.
        section2: The body under ``## 2. Interfaces``, or None for a design
            without a ``## 2.`` heading.
        section1_extra: Text appended to section 1.
        section3: The body under ``## 3. Changes to existing interfaces``.
        version: The front matter's version.

    Returns:
        The document text.
    """
    text = (front_matter(f"{feature.id}-design", "en", version, "design.zh-CN.md")
            + f"# {feature.id} {feature.name}: interface design\n\n"
            f"## 1. Feature\n\n- ID and name: {feature.id} {feature.name}\n"
            "- Hard dependencies: None\n- Soft dependencies: None\n\n" + section1_extra)
    if section2 is not None:
        text += "## 2. Interfaces\n\n" + section2 + "\n"
    return text + ("## 3. Changes to existing interfaces\n\n" + section3 + "\n"
                   "## 4. Architect review\n\n| Item | Result | Note |\n| --- | --- | --- |\n"
                   "| Fits the module layout and the data model | Pass | None |\n\n"
                   "## 5. Change log\n\n| Version | Date | Change |\n| --- | --- | --- |\n"
                   "| 0.1 | 2026-11-01 | First draft. |\n")


def custom_design_step(feature: Feature, design: Optional[str]) -> Step:
    """Stage 1 of a feature merged with a chosen English design, or with none.

    Args:
        feature: The feature.
        design: The English design's text, or None for a stage 1 commit
            that leaves no ``design.md`` in the feature folder.

    Returns:
        The step.
    """
    mirror = (front_matter(f"{feature.id}-design", "zh-CN", "1.0", "design.md")
              + f"# {feature.id} {feature.name}：接口设计\n\n## 1. 功能\n\n无\n")
    if design is None:
        return step(feature.title(1), {f"{feature.folder}/notes.md": "# Notes\n"})
    return step(feature.title(1), {feature.design: design,
                                   f"{feature.folder}/design.zh-CN.md": mirror})


def _data(content: bytes) -> bytes:
    """A fast-import ``data`` command for exact bytes."""
    return b"data %d\n" % len(content) + content + b"\n"


def _commit_block(ref: str, mark: int, message: str, files: Iterable, parent: Optional[int],
                  merge: Optional[int], when: int) -> bytes:
    """One fast-import ``commit`` command.

    Args:
        ref: The branch ref the commit goes on.
        mark: This commit's mark.
        message: The commit message.
        files: ``(path, content)`` pairs; None content deletes.
        parent: The first parent's mark, or None for a root commit.
        merge: The second parent's mark, or None.
        when: The author and committer time, in seconds since the epoch.

    Returns:
        The command's bytes.
    """
    parts = [f"commit {ref}\nmark :{mark}\n".encode(),
             f"author Test Author <{EMAIL}> {when} +0000\n".encode(),
             f"committer Test Committer <{EMAIL}> {when} +0000\n".encode(),
             _data((message + "\n").encode("utf-8"))]
    if parent is not None:
        parts.append(f"from :{parent}\n".encode())
    if merge is not None:
        parts.append(f"merge :{merge}\n".encode())
    for path, content in files:
        if content is None:
            parts.append(f"D {path}\n".encode())
        else:
            parts.append(f"M 100644 inline {path}\n".encode() + _data(as_bytes(content)))
    parts.append(b"\n")
    return b"".join(parts)


def _import_stream(steps: Sequence[Step]) -> bytes:
    """A fast-import stream that builds ``main`` from the steps, oldest first."""
    out, mark, tip, when = [], 0, None, 1762470000
    for item in steps:
        when += 60
        if item.merge is None:
            mark += 1
            out.append(_commit_block("refs/heads/main", mark, item.subject, item.files, tip,
                                     None, when))
            tip = mark
            continue
        mark += 1
        side = mark
        out.append(_commit_block("refs/heads/side", side, item.subject, item.files, tip, None,
                                 when))
        mark += 1
        out.append(_commit_block("refs/heads/main", mark, item.merge, (), tip, side, when + 30))
        tip = mark
    return b"".join(out)


def origin_repo(steps: Sequence[Step]) -> Path:
    """A cached bare origin whose ``main`` is built from the steps.

    The steps are imported into a seed repository's ``main``, and the origin
    is made from the seed with ``git clone --bare``.

    Args:
        steps: The history of ``main``, oldest first.

    Returns:
        The bare origin. Never change it.
    """
    key = repr(tuple(steps))
    if key not in _ORIGINS:
        seed = new_dir("seed")
        git(seed, "init", "-q", "-b", "main")
        git(seed, "fast-import", "--quiet", input_bytes=_import_stream(steps))
        if any(item.merge for item in steps):
            git(seed, "update-ref", "-d", "refs/heads/side")
        bare = SCRATCH / f"origin{next(_COUNTER)}.git"
        git(SCRATCH, "clone", "-q", "--bare", str(seed), str(bare))
        _ORIGINS[key] = bare
    return _ORIGINS[key]


# -------------------------------------------------------------------- fakes

_FAKE_SOURCE = r'''
"""A stand-in for gh or mamba in the F07 tests. It records each call and
never touches the network."""
import json
import os
import sys
from pathlib import Path

LOG = Path(@LOG@)
DATA = Path(@DATA@)
KIND = @KIND@


def main():
    """Records the call, then answers as the data file says."""
    args = sys.argv[1:]
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"argv": args, "cwd": os.getcwd()}) + "\n")
    data = json.loads(DATA.read_text(encoding="utf-8")) if DATA.is_file() else {}
    if KIND != "gh" or data.get("fail"):
        sys.stderr.write("fake " + KIND + ": this call fails on purpose\n")
        return 1
    if args[:2] == ["pr", "list"]:
        sys.stdout.write(json.dumps(data.get("prs", [])) + "\n")
        return 0
    if args[:2] == ["pr", "view"] and len(args) > 2:
        comments = data.get("comments", {}).get(args[2], [])
        sys.stdout.write(json.dumps({"comments": comments}) + "\n")
        return 0
    sys.stderr.write("fake gh: unknown call\n")
    return 4


sys.exit(main())
'''


def _launcher(folder: Path, name: str, log: Path, data: Path) -> Path:
    """Writes a fake program: a POSIX script, or a ``.bat`` that runs Python on Windows.

    Args:
        folder: The folder that goes first on the PATH.
        name: ``gh`` or ``mamba``.
        log: The file each call is appended to, as a JSON line.
        data: The JSON file the fake answers from.

    Returns:
        The launcher's path.
    """
    source = (_FAKE_SOURCE.replace("@LOG@", repr(str(log))).replace("@DATA@", repr(str(data)))
              .replace("@KIND@", repr(name)))
    if os.name == "nt":
        script = folder / f"fake_{name}.py"
        script.write_text(source, encoding="utf-8")
        path = folder / f"{name}.bat"
        path.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n'
                        "exit /b %ERRORLEVEL%\r\n", encoding="utf-8")
        return path
    path = folder / name
    path.write_text(f"#!{sys.executable}\n{source}", encoding="utf-8")
    path.chmod(0o755)
    return path


class Fakes:
    """A fake gh and a fake mamba in one folder, with call logs.

    The fake gh serves ``gh pr list`` and ``gh pr view <n> --json comments``
    from a JSON file; any other call, or every call when it is set to fail,
    exits with a code other than 0. The fake mamba always fails, and no
    engine command may run it.

    Attributes:
        folder: The folder that goes first on the PATH.
        gh: The fake gh launcher.
        mamba: The fake mamba launcher.
    """

    def __init__(self, prs: Sequence[Mapping] = (), comments: Optional[Mapping] = None,
                 fail: bool = False) -> None:
        """Writes both launchers and the gh answers.

        Args:
            prs: What ``gh pr list`` prints.
            comments: PR number mapped to its comments, oldest first.
            fail: Whether every gh call fails.
        """
        self.folder = new_dir("fakes")
        self._gh_log = self.folder / "gh_calls.jsonl"
        self._mamba_log = self.folder / "mamba_calls.jsonl"
        self._data = self.folder / "gh_data.json"
        self.gh = _launcher(self.folder, "gh", self._gh_log, self._data)
        self.mamba = _launcher(self.folder, "mamba", self._mamba_log, self.folder / "none.json")
        self.serve(prs, comments, fail)

    def serve(self, prs: Sequence[Mapping] = (), comments: Optional[Mapping] = None,
              fail: bool = False) -> None:
        """Sets what the fake gh answers.

        Args:
            prs: What ``gh pr list`` prints.
            comments: PR number mapped to its comments, oldest first.
            fail: Whether every gh call fails.
        """
        data = {"prs": list(prs), "fail": fail,
                "comments": {str(k): list(v) for k, v in (comments or {}).items()}}
        write_file(self.folder, self._data.name, json.dumps(data))

    @staticmethod
    def _read(log: Path) -> list:
        """Reads a call log as a list of dicts with argv and cwd."""
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def gh_calls(self) -> list:
        """Every recorded gh call, oldest first: dicts with argv and cwd."""
        return self._read(self._gh_log)

    def mamba_calls(self) -> list:
        """Every recorded mamba call, oldest first."""
        return self._read(self._mamba_log)

    def clear(self) -> None:
        """Forgets the calls recorded so far."""
        for log in (self._gh_log, self._mamba_log):
            if log.exists():
                log.unlink()

    def path_env(self) -> dict:
        """A PATH whose first folder holds the fakes."""
        rest = os.environ.get("PATH", "")
        return {"PATH": str(self.folder) + (os.pathsep + rest if rest else "")}


def pr(number: int, title: str, branch: Optional[str] = None) -> dict:
    """One entry of ``gh pr list --json number,title,headRefName,url``.

    Args:
        number: The PR number.
        title: The PR title.
        branch: The head branch, or None for ``troy-mode/pr-<number>``.

    Returns:
        The entry.
    """
    return {"number": number, "title": title, "headRefName": branch or f"troy-mode/pr-{number}",
            "url": f"https://github.com/{LOGIN}/{PROJECT}/pull/{number}"}


def stage_pr(number: int, feature: Feature, stage: int) -> dict:
    """An open PR of one feature stage, on that stage's branch.

    Args:
        number: The PR number.
        feature: The feature.
        stage: The stage number.

    Returns:
        The ``gh pr list`` entry.
    """
    return pr(number, feature.title(stage), feature.branch(stage))


def comments(*bodies: str) -> list:
    """Comments for ``gh pr view --json comments``, oldest first, all by Troy's account.

    Every role acts through Troy's account, so the author never tells F07's
    comments from Troy's; only the heading does (F07 design 8.4).

    Args:
        *bodies: The comment bodies, oldest first.

    Returns:
        The comment entries.
    """
    return [{"author": {"login": LOGIN}, "body": body,
             "createdAt": f"2026-11-07T10:{index:02d}:00Z"}
            for index, body in enumerate(bodies)]


# ------------------------------------------------------------------ running

@dataclass
class Outcome:
    """A finished engine run.

    Attributes:
        code: The exit code.
        stdout: Standard output.
        stderr: Standard error.
        report: The parsed JSON report, or None.
    """

    code: int
    stdout: str
    stderr: str
    report: Optional[dict]

    def describe(self) -> str:
        """The run's output, for assertion messages."""
        return f"exit {self.code}\nstdout:\n{self.stdout[-6000:]}\nstderr:\n{self.stderr[-4000:]}"


def run_engine(args: Sequence, cwd: Path, fakes: Optional[Fakes] = None,
               env_extra: Optional[Mapping[str, str]] = None) -> Outcome:
    """Runs ``troy_flow.py`` with this Python and parses the report when ``--json`` is given.

    Args:
        args: The arguments after the script.
        cwd: The working folder.
        fakes: The fakes to put first on the PATH, or None for a fresh set
            whose gh fails on every call.
        env_extra: More environment variables.

    Returns:
        The outcome.
    """
    args = [str(a) for a in args]
    fakes = fakes if fakes is not None else Fakes(fail=True)
    env = base_env({**fakes.path_env(), **(env_extra or {})})
    proc = subprocess.run([sys.executable, str(ENGINE), *args], cwd=str(cwd), env=env,
                          capture_output=True, stdin=subprocess.DEVNULL, timeout=180,
                          check=False)
    stdout = proc.stdout.decode("utf-8", "replace")
    report = None
    if "--json" in args:
        try:
            report = json.loads(stdout)
        except ValueError:
            report = None
    return Outcome(proc.returncode, stdout, proc.stderr.decode("utf-8", "replace"), report)


class Project:
    """A clone of a bare origin, on a branch made from ``origin/main``.

    Attributes:
        origin: The bare origin.
        tmp: The folder that holds the clone.
        root: The clone's working tree.
    """

    def __init__(self, steps: Sequence[Step], branch: Optional[str] = WORK_BRANCH) -> None:
        """Clones the origin built from the steps and switches to a new branch.

        Args:
            steps: The history of ``origin/main``, oldest first.
            branch: The branch to make from ``origin/main``, or None to stay on main.
        """
        self.origin = origin_repo(steps)
        self.tmp = new_dir("case")
        self.root = self.tmp / PROJECT
        git(self.tmp, "clone", "-q", str(self.origin), PROJECT)
        if branch:
            self.git("switch", "-q", "-c", branch, "origin/main")

    def git(self, *args: str) -> str:
        """Runs git in the clone and returns its output."""
        return git(self.root, *args)

    def write(self, rel: str, content: Union[str, bytes]) -> None:
        """Writes a file in the working tree with the exact bytes given."""
        write_file(self.root, rel, content)

    def read_bytes(self, rel: str) -> bytes:
        """A working-tree file's bytes."""
        return (self.root / rel).read_bytes()

    def read(self, rel: str) -> str:
        """A working-tree file's text."""
        return (self.root / rel).read_bytes().decode("utf-8")

    def exists(self, rel: str) -> bool:
        """Whether a working-tree path exists."""
        return (self.root / rel).exists()

    def remove(self, rel: str) -> None:
        """Deletes a working-tree file if it exists."""
        path = self.root / rel
        if path.exists():
            path.unlink()

    def head(self) -> str:
        """The full ID of HEAD."""
        return self.git("rev-parse", "HEAD").strip()

    def branch(self) -> Optional[str]:
        """The current branch, or None when detached."""
        proc = git_proc(self.root, "symbolic-ref", "-q", "--short", "HEAD")
        return proc.stdout.strip() if proc.returncode == 0 else None

    def git_dir(self) -> Path:
        """The clone's (or worktree's) own git folder."""
        return Path(self.git("rev-parse", "--absolute-git-dir").strip())

    def status_lines(self) -> list:
        """``git status --porcelain=v1 --untracked-files=all`` as sorted lines."""
        out = self.git("status", "--porcelain=v1", "--untracked-files=all")
        return sorted(line for line in out.splitlines() if line)

    def commit(self, subject: str, files: Mapping[str, Content]) -> str:
        """Writes files, commits them on the current branch, and returns the new HEAD.

        Args:
            subject: The commit message.
            files: Paths mapped to content; None deletes.

        Returns:
            The new HEAD's ID.
        """
        for rel, content in files.items():
            if content is None:
                self.git("rm", "-q", "--", rel)
            else:
                self.write(rel, content)
                self.git("add", "--", rel)
        self.git("commit", "-q", "-m", subject)
        return self.head()

    def run(self, *args: str, fakes: Optional[Fakes] = None,
            env_extra: Optional[Mapping[str, str]] = None, repo_option: bool = True,
            cwd: Optional[Path] = None) -> Outcome:
        """Runs the engine on this clone with ``--json``.

        Args:
            *args: The subcommand and its options.
            fakes: The fakes on the PATH, or None for a gh that fails on every call.
            env_extra: More environment variables.
            repo_option: Whether to pass ``--repo`` and run from outside the clone.
            cwd: The working folder when ``repo_option`` is false; default the root.

        Returns:
            The outcome.
        """
        if repo_option:
            return run_engine([*args, "--repo", self.root, "--json"], self.tmp, fakes, env_extra)
        return run_engine([*args, "--json"], cwd or self.root, fakes, env_extra)

    def status(self, *extra: str, prs: Sequence[Mapping] = (),
               comments_by_pr: Optional[Mapping] = None, fakes: Optional[Fakes] = None,
               env_extra: Optional[Mapping[str, str]] = None) -> Outcome:
        """Runs ``status --json`` with a fake gh that serves the given PRs.

        Args:
            *extra: More status options, such as ``--write-progress``.
            prs: The open PRs.
            comments_by_pr: PR number mapped to its comments.
            fakes: Fakes to use instead of new ones built from ``prs``.
            env_extra: More environment variables.

        Returns:
            The outcome.
        """
        fakes = fakes if fakes is not None else Fakes(prs, comments_by_pr)
        return self.run("status", *extra, fakes=fakes, env_extra=env_extra)


def status_runs(cases: Mapping[str, Sequence]) -> dict:
    """Builds one clone per case and runs ``status --json`` on all of them side by side.

    Args:
        cases: A name mapped to ``(steps, prs)`` or ``(steps, prs, comments_by_pr)``.

    Returns:
        Each name mapped to its outcome.
    """
    def run(case: Sequence) -> Outcome:
        """Clones one origin and runs status in it."""
        steps, prs = case[0], case[1]
        by_pr = case[2] if len(case) > 2 else None
        return Project(steps).status(prs=prs, comments_by_pr=by_pr)
    names = list(cases)
    return dict(zip(names, parallel(run, [cases[name] for name in names])))


# ------------------------------------------------------------------ reading

def progress_fields(text: str) -> dict:
    """The progress file's field lines: field name mapped to the text after ``: ``.

    Args:
        text: The progress file.

    Returns:
        Each ``- <Field>: <value>`` line's value by field.
    """
    found = {}
    for line in text.split("\n"):
        match = re.match(r"^- ([A-Za-z ]+):(?: (.*))?$", line)
        if match and match.group(1) in PROGRESS_FIELDS:
            found[match.group(1)] = (match.group(2) or "").strip()
    return found


def progress_issues(text: str) -> list:
    """The sub-items under the progress file's ``- Open issues:`` line.

    Args:
        text: The progress file.

    Returns:
        The note texts, in order.
    """
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("- Open issues:")), None)
    if start is None:
        return []
    issues = []
    for line in lines[start + 1:]:
        if not line.startswith("  - "):
            break
        issues.append(line[4:])
    return issues


def split_command(command: str) -> list:
    """Splits a check's command line the way bash would.

    Args:
        command: The command line.

    Returns:
        Its words.
    """
    return shlex.split(command, posix=True)


def pack_words(command: str) -> tuple:
    """Splits a pack step into its mamba program, its target, and the rest.

    Args:
        command: A check that starts ``<mamba> run <target> ``.

    Returns:
        ``(program, target words, rest words)``; the target is
        ``["-n", <environment>]`` or ``["-p", <prefix>]``.

    Raises:
        AssertionError: The command does not start with ``<mamba> run -n|-p``.
    """
    words = split_command(command)
    if len(words) < 4 or words[1] != "run" or words[2] not in ("-n", "-p"):
        raise AssertionError(f"not a pack step: {command!r}")
    return words[0], words[2:4], words[4:]


def troy_check_step(checks: Sequence[str]) -> list:
    """The words of the one check that runs ``troy_check.py code``.

    Args:
        checks: The brief's checks.

    Returns:
        The words from ``python`` on.

    Raises:
        AssertionError: There is not exactly one such check.
    """
    found = [c for c in checks if "troy_check.py" in c]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} troy_check.py steps in {checks!r}")
    words = split_command(found[0])
    start = next((i for i, w in enumerate(words) if w.endswith("troy_check.py")), None)
    if start is None or start == 0:
        raise AssertionError(f"no python before troy_check.py in {found[0]!r}")
    return words[start - 1:]


def option_value(words: Sequence[str], option: str) -> Optional[str]:
    """The word after an option, or None when the option is absent.

    Args:
        words: Command words.
        option: For example ``--title``.

    Returns:
        The value.
    """
    words = list(words)
    if option not in words or words.index(option) + 1 >= len(words):
        return None
    return words[words.index(option) + 1]


# ---------------------------------------------------------------- test case

class FlowCase(unittest.TestCase):
    """Assertions shared by the F07 engine tests."""

    maxDiff = 20000

    def report_of(self, out: Outcome, code: int = 0, command: Optional[str] = None) -> dict:
        """Asserts the exit code and the report's common keys, and returns the report.

        Args:
            out: The run.
            code: The expected exit code, 0 or 1.
            command: The expected ``command`` value, or None to skip it.

        Returns:
            The report.
        """
        self.assertEqual(out.code, code, out.describe())
        self.assertIsInstance(out.report, dict, out.describe())
        self.assertIs(out.report.get("ok"), code == 0, out.describe())
        self.assertIsInstance(out.report.get("notes"), list, out.describe())
        self.assertIsInstance(out.report.get("problems"), list, out.describe())
        if command is not None:
            self.assertEqual(out.report.get("command"), command, out.describe())
        return out.report

    def assert_next(self, report: dict, **expected) -> None:
        """Asserts ``next``: the named keys equal the values, the others are null.

        Keys a row of the note's table does not name are null, except
        ``rounds`` and ``attempts``, which are 0. Pass ``ANY`` to skip a key.

        Args:
            report: The status report.
            **expected: Key names of ``next`` mapped to their values.
        """
        nxt = report.get("next")
        self.assertIsInstance(nxt, dict, json.dumps(report, indent=1)[:4000])
        for key in NEXT_KEYS:
            want = expected.get(key, 0 if key in ("rounds", "attempts") else None)
            if want is ANY:
                continue
            self.assertEqual(nxt.get(key), want, f"next.{key} in {json.dumps(nxt)}")

    def assert_exit(self, out: Outcome, code: int) -> None:
        """Asserts the exit code alone.

        Args:
            out: The run.
            code: The expected exit code.
        """
        self.assertEqual(out.code, code, out.describe())


def problem_kinds(report: dict) -> list:
    """The sorted ``(kind, path)`` pairs of a check-run report's problems.

    Args:
        report: The report.

    Returns:
        The pairs.
    """
    return sorted((p.get("kind"), p.get("path")) for p in report.get("problems", []))


def hooks_line(time_text: str, agent_type: Optional[str], agent_id: Optional[str],
               rule: str = "scope", path: str = "docs/x.md") -> dict:
    """One line of ``<git dir>/troy-mode/hooks.log`` (F05 design 10).

    Args:
        time_text: The ``time`` value, ``YYYY-MM-DDTHH:MM:SSZ``.
        agent_type: The ``agent_type`` value.
        agent_id: The ``agent_id`` value; None for the main session.
        rule: The ``rule`` value.
        path: The one path in ``paths``.

    Returns:
        The entry.
    """
    return {"time": time_text, "session": "s1", "agent_id": agent_id, "agent_type": agent_type,
            "event": "PreToolUse", "tool": "Write", "rule": rule, "paths": [path],
            "subcommand": None, "decision": "deny"}
