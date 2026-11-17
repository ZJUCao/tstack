"""Shared fixtures for the F15 tests, issues for Troy (F15 design 13.1; F15 interface note).

Builders for what the fake gh serves (issues in every state, PRs in every
state, reviews), a Chinese requirements mirror with a features table, a
release whose version test plan has scenarios Troy runs in both languages,
runs of ``troy_flow.py issues``, and the checks every rendered body shares:
the marker line first, the Chinese part before the folded English part, the
boxes in the Chinese part only, no time stamp, and full URLs (design 8).
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence

from flow_helpers import (
    CHANGE_PREFIX, F01, F02, LOGIN, REPO_URL, REQUIREMENTS, REQUIREMENTS_ZH, TWO, Fakes,
    FlowCase, Outcome, Project, base_files, base_step, bug_step, chinese_acceptance, comments,
    front_matter, merged_pr, parallel, release_pr, release_step, release_title,
    requirements_text, run_engine, same_path, stages, step, version_plan_text,
    version_tests_step,
)

BLOB = REPO_URL + "/blob/main/"
DETAILS = "<details><summary>English</summary>"
ALL_LABELS = ("bug", "idea", "progress", "device-test")
READ_CALLS = {("pr", "list"), ("pr", "view"), ("issue", "list"), ("issue", "view"),
              ("label", "list"), ("repo", "view"), ("release", "list")}
ZH_NAMES = {"F01": "数单词", "F02": "数行数", "F03": "数字符", "F04": "报告总数",
            "F05": "监视文件夹"}
ZH_STATUS = {"Not started": "未开始", "Passes tests on main": "在 main 上通过测试",
             "Ran for real on Troy's PC": "在 Troy 的电脑上真跑过",
             "Usable on Troy's devices": "在 Troy 的设备上可用"}
LABELS = (
    ("idea", "FBCA04", "An idea or change for troy-mode to take in / 交给 troy-mode 的想法或改动"),
    ("progress", "1D76DB", "A feature's progress, kept by troy-mode / 功能进度，由 troy-mode 维护"),
    ("device-test", "0E8A16",
     "What Troy tests on Troy's devices for a release / 发布前 Troy 在自己设备上测的项目"),
)
# The comment headings of design 8.4, each as a first line.
HEADINGS = ("Idea: requirement change", "Idea: bug", "Idea: rule", "Idea: answered",
            "Idea: later", "Idea: in the requirements",
            "Waiting for Troy: which version should it go in", "Reply to Troy",
            "Device test, run 2: ready")
STAGE_ZH = {1: "接口设计", 2: "测试计划", 3: "模拟", 4: "测试", 5: "实现", 6: "验收"}
STAGE_EN = {1: "Interface design", 2: "Test plan", 3: "Mock", 4: "Tests", 5: "Implementation",
            6: "Acceptance"}
FOOT_ZH = "troy-mode 维护这段文字，改动会被替换。想对 troy-mode 说什么，请写评论。"
FOOT_EN = "troy-mode keeps this text and replaces edits to it. To reach troy-mode, write a comment."
HOW_ZH = "测完一项、结果和预期一样，就勾上它。哪一项不对，就不勾，写一条评论说明。全部通过后，勾最后一项。"
HOW_EN = ("When a scenario works as expected, tick it. If one does not, leave it unticked and "
          "write a comment. When all pass, tick the last box.")
BOX = re.compile(r"^\s*- \[[ xX]\]")
STAMP = re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d\d:\d\d(:\d\d)?\b")
LINK = re.compile(r"\]\(([^)]*)\)")
SAFE_WORD = re.compile(r"^[A-Za-z0-9_./:=@%+,-]+$")


# --------------------------------------------------------------- documents

def zh_requirements(features: Sequence = TWO, version: str = "1.0",
                    statuses: Optional[Mapping[str, str]] = None) -> str:
    """The Chinese requirements mirror with a features table (requirements template 4).

    Args:
        features: The table's rows, in the English table's order.
        version: The front matter's version.
        statuses: Feature ID mapped to its Chinese Status cell, or None to
            translate each English cell with ``ZH_STATUS``.

    Returns:
        The document text.
    """
    rows = []
    for item in features:
        status = (statuses or {}).get(item.id) or ZH_STATUS.get(item.status, item.status)
        rows.append(f"| {item.id} | {ZH_NAMES[item.id]} | {', '.join(item.hard) or '无'} "
                    f"| {', '.join(item.soft) or '无'} | {item.version} | {status} |")
    return (front_matter("requirements", "zh-CN", version, "requirements.md")
            + "# wordcount 需求\n\n## 1. 目标\n\n统计文本文件中的单词数。\n\n## 4. 功能点\n\n"
            "| 编号 | 功能 | 硬依赖 | 软依赖 | 版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")


def project_files(features: Sequence = TWO, statuses: Optional[Mapping[str, str]] = None,
                  extra: Optional[Mapping] = None, **kwargs) -> dict:
    """``base_files`` with a Chinese mirror that has a features table.

    Args:
        features: The features table.
        statuses: Chinese Status cells by feature ID, as for ``zh_requirements``.
        extra: More files, which replace the defaults of the same path.
        **kwargs: Passed on to ``base_files``.

    Returns:
        Paths mapped to content.
    """
    files = base_files(features, **kwargs)
    files[REQUIREMENTS_ZH] = zh_requirements(features, statuses=statuses)
    files.update(extra or {})
    return files


def requirements_pair(features: Sequence, version: str = "2.0",
                      statuses: Optional[Mapping[str, str]] = None) -> dict:
    """Both requirements files at one version, the mirror with its features table."""
    return {REQUIREMENTS: requirements_text(features, version=version),
            REQUIREMENTS_ZH: zh_requirements(features, version, statuses)}


def zh_change_step(summary: str, features: Sequence, version: str = "2.0",
                   statuses: Optional[Mapping[str, str]] = None):
    """A merged ``[docs] Change the requirements: <summary>`` PR that changes both files."""
    return step(CHANGE_PREFIX + summary, requirements_pair(features, version, statuses))


def progress_title(feature) -> str:
    """A progress issue's title, for example ``F01 数单词 / Count words`` (note 4.1)."""
    return f"{feature.id} {ZH_NAMES[feature.id]} / {feature.name}"


def checklist_title(tag: str) -> str:
    """A checklist's title (note 4.2)."""
    return f"{tag} 在你的设备上测试 / Test {tag} on your devices"


# ----------------------------------------------------------- gh's answers

def at(minutes: int, day: int = 8) -> str:
    """A GitHub time stamp a number of minutes after midnight of a November 2026 day."""
    moment = datetime(2026, 11, day, tzinfo=timezone.utc) + timedelta(minutes=minutes)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def issue_comments(*bodies: str, start: int = 0) -> list:
    """Comments of ``gh issue list --json comments``, oldest first, all by Troy's account."""
    return [{"body": body, "createdAt": at(start + index), "author": {"login": LOGIN}}
            for index, body in enumerate(bodies)]


def gh_issue(number: int, title: str, body: str = "", labels: Sequence[str] = (),
             comment_bodies: Sequence[str] = (), state: str = "OPEN",
             reason: Optional[str] = None) -> dict:
    """One issue of ``gh issue list --state all`` (note section 1); a higher number is newer."""
    return {"number": number, "title": title, "labels": [{"name": n} for n in labels],
            "body": body, "comments": issue_comments(*comment_bodies, start=number * 2),
            "url": f"{REPO_URL}/issues/{number}", "createdAt": at(number, day=2),
            "state": state, "stateReason": reason, "author": {"login": LOGIN}}


def progress_marker(feature_id: str) -> str:
    """A progress issue's first line (design 8.1)."""
    return f"<!-- troy-mode: progress {feature_id} -->"


def checklist_marker(tag: str) -> str:
    """A checklist's first line (design 8.1)."""
    return f"<!-- troy-mode: device-test {tag} -->"


def progress_issue(number: int, feature_id: str, body: Optional[str] = None,
                   title: Optional[str] = None, state: str = "OPEN",
                   reason: Optional[str] = None, comment_bodies: Sequence[str] = ()) -> dict:
    """A progress issue; by default its body is out of date (the marker and one old line)."""
    text = body if body is not None else progress_marker(feature_id) + "\nOld text.\n"
    return gh_issue(number, title or f"{feature_id} old title", text, ("progress",),
                    comment_bodies, state, reason)


def checklist_issue(number: int, tag: str, body: Optional[str] = None,
                    title: Optional[str] = None, state: str = "OPEN",
                    reason: Optional[str] = None, comment_bodies: Sequence[str] = ()) -> dict:
    """A checklist issue; by default its body is out of date."""
    text = body if body is not None else checklist_marker(tag) + "\nOld text.\n"
    return gh_issue(number, title or checklist_title(tag), text, ("device-test",),
                    comment_bodies, state, reason)


def all_pr(number: int, title: str, state: str = "MERGED") -> dict:
    """One entry of ``gh pr list --state all --json number,title,state,url``."""
    return {"number": number, "title": title, "state": state,
            "url": f"{REPO_URL}/pull/{number}"}


def stage_prs(feature, upto: int, base: int = 40) -> list:
    """Merged stage PRs 1 to ``upto`` of a feature, numbered ``base`` plus the stage."""
    return [all_pr(base + n, feature.title(n)) for n in range(1, upto + 1)]


def review(body: str, submitted: str, state: str = "COMMENTED") -> dict:
    """One review of ``gh pr view --json reviews``."""
    return {"body": body, "submittedAt": submitted, "state": state,
            "author": {"login": LOGIN}}


# ---------------------------------------------------------------- release

COMMIT1 = "34a7728" + "e" * 33
COMMIT2 = "9c1f0de" + "a" * 33
TAG = "v0.1.0"
RELEASE_FEATURES = (replace(F01, status="Passes tests on main"),
                    replace(F02, status="Passes tests on main"))
EN_SCENARIOS = (
    ("v0.1-S01", "Count words and lines", "Claude", "Run wc on a file of three words",
     "Prints 3 words"),
    ("v0.1-S02", "Count on Troy's laptop", "Troy", "Open a terminal and run wc notes.txt",
     "Prints the count"),
    ("v0.1-S04", "Read Chinese text in Windows Terminal", "Troy",
     "Run wc on a Chinese file in Windows Terminal", "The count shows and the text is readable"),
)
ZH_SCENARIOS = (
    ("v0.1-S01", "统计单词和行数", "Claude", "对三个单词的文件运行 wc", "显示 3 个单词"),
    ("v0.1-S02", "在 Troy 的笔记本上统计", "Troy", "打开终端，运行 wc notes.txt", "显示统计结果"),
    ("v0.1-S04", "在 Windows Terminal 里读中文", "Troy", "在 Windows Terminal 里对中文文件运行 wc",
     "显示统计结果，中文可读"),
)
EN_PERF = (("v0.1-S03", "PT01", "10 MB file", "1 run", "Troy's PC", "Claude"),
           ("v0.1-S05", "PT02", "100 MB file", "3 runs", "Troy's laptop", "Troy"))
ZH_PERF = (("v0.1-S03", "PT01", "10 MB 文件", "1 次", "Troy 的电脑", "Claude"),
           ("v0.1-S05", "PT02", "100 MB 文件", "3 次", "Troy 的笔记本", "Troy"))
EN_DEVICES = (("Troy's PC", "Windows 11", "Claude"), ("Troy's laptop", "macOS 15", "Troy"),
              ("Troy's phone", "Android 16", "Troy"))
ZH_DEVICES = (("Troy 的电脑", "Windows 11", "Claude"), ("Troy 的笔记本", "macOS 15", "Troy"),
              ("Troy 的手机", "Android 16", "Troy"))
TROY_IDS = ("v0.1-S02", "v0.1-S04", "v0.1-S05")
RETRO = "Retrospective: v0.1.0\n\nNothing repeated in two or more PRs."


def plan_pair(scenarios: Sequence = (EN_SCENARIOS, ZH_SCENARIOS),
              perf: Sequence = (EN_PERF, ZH_PERF), acceptance: Optional[Sequence] = None,
              version: str = "v0.1", features: Sequence[str] = ("F01", "F02")) -> dict:
    """A version test plan and a mirror with different text in each language.

    Args:
        scenarios: ``(English rows, Chinese rows)`` of section 2.
        perf: ``(English rows, Chinese rows)`` of section 3.
        acceptance: English acceptance rows, or None for an empty record.
        version: For example ``v0.1``.
        features: The ``- Features:`` IDs.

    Returns:
        Paths mapped to text.
    """
    zh_acceptance = chinese_acceptance(acceptance) if acceptance else None
    return {f"docs/versions/{version}/test-plan.md": version_plan_text(
                version, features, "en", scenarios=scenarios[0], perf=perf[0],
                devices=EN_DEVICES, acceptance=acceptance),
            f"docs/versions/{version}/test-plan.zh-CN.md": version_plan_text(
                version, features, "zh-CN", scenarios=scenarios[1], perf=perf[1],
                devices=ZH_DEVICES, acceptance=zh_acceptance)}


def release_steps(plan: Optional[Mapping] = None, tested: bool = True,
                  features: Sequence = RELEASE_FEATURES) -> list:
    """A project whose v0.1 features are accepted, with ``plan_pair`` as its plan.

    Args:
        plan: The plan files, or None for ``plan_pair()``.
        tested: Whether the version tests have merged.
        features: The features table.

    Returns:
        The steps.
    """
    files = project_files(features, extra=plan if plan is not None else plan_pair())
    steps = [base_step(files), *stages(F01, 6), *stages(F02, 6)]
    return steps + ([version_tests_step("v0.1")] if tested else [])


def passed(run: int, commit: str) -> str:
    """A ``Release test, run <n>: passed`` comment with its ``Commit tested:`` line."""
    return (f"Release test, run {run}: passed\n\nCommit tested: {commit}\n\n"
            "v0.1-S01 passed.\nv0.1-S03 passed.")


def waiting(tag: str = TAG) -> str:
    """F08's request to Troy on the release PR."""
    return f"Waiting for Troy: accept {tag}"


def release_fakes(*bodies: str, all_issues: Sequence = (), number: int = 30, tag: str = TAG,
                  labels: Sequence[str] = ALL_LABELS, **more) -> dict:
    """Fakes keyword arguments for an open release PR with its comments."""
    return {"prs": [release_pr(number, tag)], "comments": {number: comments(*bodies)},
            "all_issues": list(all_issues), "labels": list(labels), **more}


def released_steps() -> list:
    """v0.1.0 released: the release commit with Troy's acceptance in the plan."""
    accepted = plan_pair(acceptance=[("2026-11-09", f"Accepted as {TAG}", "None")])
    return release_steps() + [release_step(TAG, accepted)]


def patched_steps() -> list:
    """v0.1.0 released, then bugs B14 and B9 fixed: a patch v0.1.1 may follow."""
    fixes = [bug_step(bug, kind, f"Bug {bug}") for bug in ("B14", "B9")
             for kind in ("test", "fix")]
    return released_steps() + fixes


def patch_fakes(*bodies: str, all_issues: Sequence = ()) -> dict:
    """Fakes for the open patch release PR #60 of v0.1.1, after v0.1.0's GitHub release."""
    return {"prs": [release_pr(60, "v0.1.1")],
            "comments": {40: comments(RETRO), 60: comments(*bodies)},
            "merged": [merged_pr(40, release_title(TAG))], "releases": [TAG],
            "all_issues": list(all_issues), "labels": list(ALL_LABELS)}


# ------------------------------------------------------------------ running

def issues_run(steps: Sequence, fakes_kwargs: Optional[Mapping] = None,
               extra: Sequence[str] = ()) -> tuple:
    """Clones the origin built from the steps and runs ``issues --json`` in it.

    Args:
        steps: The history of ``origin/main``.
        fakes_kwargs: The fake gh's answers.
        extra: More options, such as ``--device-test-scenarios``.

    Returns:
        ``(outcome, fakes, project)``.
    """
    fakes = Fakes(**dict(fakes_kwargs or {}))
    project = Project(steps)
    return project.run("issues", *extra, fakes=fakes), fakes, project


def issues_runs(cases: Mapping[str, Sequence]) -> dict:
    """Runs ``issues_run`` for each case side by side.

    Args:
        cases: A name mapped to ``(steps, fakes keyword arguments)`` or
            ``(steps, fakes keyword arguments, extra options)``.

    Returns:
        Each name mapped to ``(outcome, fakes, project)``.
    """
    names = list(cases)
    return dict(zip(names, parallel(lambda case: issues_run(*case), [cases[n] for n in names])))


def status_run(steps: Sequence, fakes_kwargs: Optional[Mapping] = None,
               json_report: bool = True) -> tuple:
    """Clones the origin built from the steps and runs ``status`` in it.

    Args:
        steps: The history of ``origin/main``.
        fakes_kwargs: The fake gh's answers.
        json_report: Whether to pass ``--json``.

    Returns:
        ``(outcome, fakes, project)``.
    """
    fakes = Fakes(**dict(fakes_kwargs or {}))
    project = Project(steps)
    if json_report:
        return project.run("status", fakes=fakes), fakes, project
    return run_engine(["status", "--repo", project.root], project.tmp, fakes), fakes, project


def status_runs_with(cases: Mapping[str, Sequence]) -> dict:
    """Runs ``status_run`` for each case side by side.

    Args:
        cases: A name mapped to ``(steps, fakes keyword arguments)``.

    Returns:
        Each name mapped to ``(outcome, fakes, project)``.
    """
    names = list(cases)
    return dict(zip(names, parallel(lambda case: status_run(*case), [cases[n] for n in names])))


# ------------------------------------------------------------------ reading

def command_of(argv: Sequence[str]) -> str:
    """``gh`` and the words, each word with a character outside the safe set single-quoted.

    The rule of the interface note, section 4: ``A-Za-z0-9_./:=@%+,-`` are
    safe, and a ``'`` inside a quoted word is written ``'\\''``.
    """
    words = []
    for word in argv:
        if word and SAFE_WORD.match(word):
            words.append(word)
        else:
            words.append("'" + word.replace("'", "'\\''") + "'")
    return "gh " + " ".join(words)


def lines_of(text: str) -> list:
    """A text's lines, CRLF made LF."""
    return text.replace("\r\n", "\n").split("\n")


def split_body(body: str) -> tuple:
    """The Chinese part's lines and the English part's lines, split at the ``<details>`` line."""
    lines = lines_of(body)
    if DETAILS not in lines:
        return lines, []
    index = lines.index(DETAILS)
    return lines[:index], lines[index + 1:]


def nonblank(lines: Sequence[str]) -> list:
    """The lines that hold more than white space."""
    return [line for line in lines if line.strip()]


def box_lines(lines: Sequence[str]) -> list:
    """The task-list lines (``- [ ]``, ``- [x]``, ``- [X]``)."""
    return [line for line in lines if BOX.match(line)]


def tick(body: str, prefix: str, mark: str = "x") -> str:
    """The body with the box of the one line that starts ``- [ ] <prefix>`` ticked."""
    old = f"- [ ] {prefix}"
    if body.count(old) != 1:
        raise AssertionError(f"{old!r} is not in the body once:\n{body}")
    return body.replace(old, f"- [{mark}] {prefix}")


class IssuesCase(FlowCase):
    """Assertions shared by the F15 tests."""

    def issues_report(self, out: Outcome, code: int = 0) -> dict:
        """Asserts the exit code and the ``issues`` report's keys, and returns the report."""
        report = self.report_of(out, code, "issues")
        if code == 0:
            for key in ("labels", "actions", "skipped"):
                self.assertIsInstance(report.get(key), list, f"{key}: {out.describe()}")
        return report

    def assert_read_only(self, fakes: Fakes) -> None:
        """Every gh call the engine made reads; none writes (note section 1)."""
        for argv in fakes.gh_argvs():
            with self.subTest(argv=argv):
                self.assertIn(tuple(argv[:2]), READ_CALLS, f"a gh call that writes: {argv}")

    def body_of(self, action: Mapping) -> str:
        """The text of an action's body file."""
        self.assertIsInstance(action.get("body_file"), str, action)
        return Path(action["body_file"]).read_bytes().decode("utf-8")

    def assert_file_word(self, word: str, expected: Path) -> None:
        """A path word of an argv: forward slashes, and naming the expected file."""
        self.assertNotIn("\\", word)
        self.assertTrue(same_path(word, expected), f"{word} is not {expected}")

    def body_path(self, project: Project, name: str) -> Path:
        """``<git dir>/troy-mode/flow/issues/<name>.md`` (note section 4)."""
        return project.git_dir() / "troy-mode" / "flow" / "issues" / f"{name}.md"

    def assert_command(self, entry: Mapping) -> None:
        """``command`` is ``gh`` and the quoted argv (note section 4)."""
        self.assertEqual(entry.get("command"), command_of(entry["argv"]), entry)

    def assert_create(self, action: Mapping, project: Project, kind: str, item: str,
                      title: str) -> None:
        """A ``create`` action with its argv, its body file, and its command."""
        name = f"{kind}-{item}"
        self.assertEqual((action["action"], action["kind"], action["item"], action["number"],
                          action["title"], action["labels"]),
                         ("create", kind, item, None, title, [kind]), action)
        self.assertIsNone(action.get("duplicate_of"), action)
        self.assertEqual(action["argv"][:-1],
                         ["issue", "create", "--title", title, "--label", kind, "--body-file"])
        self.assert_file_word(action["argv"][-1], self.body_path(project, name))
        self.assertTrue(same_path(action["body_file"], self.body_path(project, name)), action)
        self.assert_command(action)

    def assert_edit(self, action: Mapping, project: Project, kind: str, item: str,
                    number: int, title: str) -> None:
        """An ``edit`` action with its argv, its body file, and its command."""
        name = f"{kind}-{item}"
        self.assertEqual((action["action"], action["kind"], action["item"], action["number"],
                          action["title"]), ("edit", kind, item, number, title), action)
        self.assertEqual(action["argv"][:-1],
                         ["issue", "edit", str(number), "--title", title, "--body-file"])
        self.assert_file_word(action["argv"][-1], self.body_path(project, name))
        self.assertTrue(same_path(action["body_file"], self.body_path(project, name)), action)
        self.assert_command(action)

    def assert_close(self, action: Mapping, kind: str, item: str, number: int,
                     reason: str) -> None:
        """A ``close`` action with the reason ``completed`` or ``not planned``."""
        self.assertEqual((action["action"], action["kind"], action["item"], action["number"],
                          action["reason"]), ("close", kind, item, number, reason), action)
        self.assertEqual(action["argv"], ["issue", "close", str(number), "--reason", reason])
        self.assert_command(action)

    def assert_reopen(self, action: Mapping, kind: str, item: str, number: int) -> None:
        """A ``reopen`` action."""
        self.assertEqual((action["action"], action["kind"], action["item"], action["number"]),
                         ("reopen", kind, item, number), action)
        self.assertEqual(action["argv"], ["issue", "reopen", str(number)])
        self.assert_command(action)

    def assert_duplicate(self, action: Mapping, kind: str, item: str, number: int,
                         kept: int) -> None:
        """A ``close-duplicate`` action naming the issue kept."""
        self.assertEqual((action["action"], action["kind"], action["item"], action["number"],
                          action["duplicate_of"]),
                         ("close-duplicate", kind, item, number, kept), action)
        self.assertEqual(action["argv"],
                         ["issue", "close", str(number), "--duplicate-of", str(kept)])
        self.assert_command(action)

    def assert_body_shape(self, body: str, marker: str) -> None:
        """The marker first, Chinese then the folded English, boxes once, no stamp, full URLs."""
        lines = lines_of(body)
        self.assertEqual(lines[0], marker, body)
        self.assertEqual(lines.count(DETAILS), 1, body)
        self.assertEqual(nonblank(lines)[-1], "</details>", body)
        chinese, english = split_body(body)
        self.assertRegex("\n".join(chinese), r"[\u4e00-\u9fff]", "the Chinese part comes first")
        self.assertNotRegex("\n".join(nonblank(english)[:-1]), r"[\u4e00-\u9fff]",
                            "the English part holds no Chinese text")
        self.assertNotEqual(box_lines(chinese), [], "the boxes are in the Chinese part")
        self.assertEqual(box_lines(english), [], "the English part has no boxes")
        self.assertIsNone(STAMP.search(body), "a time stamp in the body")
        for target in LINK.findall(body):
            with self.subTest(link=target):
                self.assertTrue(target.startswith(BLOB), f"not a full URL: {target}")

    def assert_in_order(self, lines: Sequence[str], expected: Sequence[str]) -> None:
        """Each expected line is one of the lines, in this order."""
        position = 0
        for want in expected:
            found = [i for i in range(position, len(lines)) if lines[i] == want]
            self.assertTrue(found, f"{want!r} not found in order in:\n" + "\n".join(lines))
            position = found[0] + 1
