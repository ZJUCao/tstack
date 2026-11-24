"""Notes for later features (tstack #67; F07 design 6.6, 14.1, 14.2, D284 to D287; F15 3.3, 4.2, 4.4, 8.4).

Written from the build contract for tstack #67 (sections A to E) before the code exists.
Black-box, as F07's and F15's tests are: ``troy_flow.py note``, ``brief``, ``status``, and
``issues`` run as subprocesses with ``--json``, a fake ``gh`` on the ``PATH`` serves issues
(comments with ``url`` and ``createdAt``) and PRs (with ``createdAt``) from JSON and records
each call with its folder, and the tests read the reports, prompts, and files.

A GitHub origin: ``remote.origin.url`` is ``https://github.com/o/r``, and
``url.<bare origin>.insteadOf`` maps it back to the local bare origin, so ``git remote
get-url origin`` gives the local path while the configured value names GitHub (contract C).
The comments' links use the fake repository's URL, ``https://github.com/ZJUCao/wordcount``.

- A, what a note is: ``BriefNotesTests`` (the comments that are no note: an idea's, a bug
  issue's, an issue whose marker is not its first line, a heading without its comma, with
  text before it, in lower case, with a one-digit ID, ``F020``, or no source; CRLF; anyone's
  comment; a closed progress issue) and ``FeatureNotesTests`` (a PR comment).
- B, ``note``: ``NoteIssueTests``, ``NoteFileTests``, ``NoteOriginMainTests``, and
  ``NoteRefusalTests``.
- C, the brief: ``BriefNotesTests``, ``BriefWithoutNotesTests``, ``OriginTests``,
  ``GhFailureTests``, and ``TeamBriefTests``.
- D, ``status``: ``FeatureNotesTests``.
- E, progress issues: ``ProgressLineTests`` and ``TroyCommentTests``.

The old brief. Each brief case runs on two clones of one origin with one set of fakes: the
GitHub clone and its twin, whose origin is the local bare folder. The twin's brief is the
brief as before this change (contract C): the tests pin its Input field to the old format
(``Input: None``, or the Input file's text right-stripped) and check that it makes no gh call.
A GitHub brief without notes must equal the twin's report byte for byte; one with notes must
equal it with only the Input field, in the prompt and in ``input``, changed.

Planted bugs of F07 design 14.2 (D284 to D287) and F15 design 13.2 caught here:

- "a note for another feature added to a brief": ``BriefNotesTests.test_each_brief_holds_
  its_block`` and ``test_only_the_items_notes``.
- "notes added to TM1's brief": ``BriefWithoutNotesTests.test_other_tasks_get_the_old_brief``
  (rows "TM1 at PR 2" and "TM1 in a [docs] side PR").
- "a note on a closed progress issue skipped": ``BriefNotesTests.test_note_on_a_closed_
  progress_issue_counts``, ``FeatureNotesTests.test_feature_notes``, and
  ``ProgressLineTests.test_target_issue_gets_the_line``.
- "a failing gh read as no notes": ``GhFailureTests.test_failing_gh_stops_the_brief`` and
  ``test_no_json_stops_the_brief``.
- "a gh call made for a repository whose origin is not on GitHub": ``OriginTests`` and
  ``BriefNotesTests.test_twin_makes_no_gh_call``.
- "a note recorded after PR 1 opened not marked late": ``FeatureNotesTests.test_feature_
  notes`` and ``test_late_design_counts_from_the_earliest_pr_1``.
- "note accepting an accepted feature": ``NoteRefusalTests.test_accepted_feature``.
- "the notes out of order": ``BriefNotesTests.test_oldest_first_with_ties``,
  ``FeatureNotesTests.test_feature_notes``, and ``ProgressLineTests``.
- F15 13.2, "a note counted as troy-mode's answer to Troy": ``TroyCommentTests.test_troys_
  comment_before_a_note_stays``.
- F15 13.2, "a note's line shown on the source feature's issue instead of the target's":
  ``ProgressLineTests.test_source_issue_gets_no_line_for_another_feature``.

Run from the repository root:
python -B -m unittest discover -s troy-mode/flow/tests -p "test_notes.py" -v
"""

import os
import re
import shlex
import sys
import unittest
from pathlib import Path
from typing import Mapping, Optional, Sequence

from flow_helpers import (
    F01, F02, F03, F04, F05, FIVE, LOGIN, REPO_URL, REQUIREMENTS, WORK_BRANCH, Fakes, Feature,
    FlowCase, Outcome, Project, base_step, bug_step, change_step, comments, git, new_dir,
    origin_repo, parallel, requirements_text, rework, run_engine, same_path, stage_pr,
    stage_step, stages, write_file,
)
from issues_helpers import (
    ALL_LABELS, READ_CALLS, IssuesCase, box_lines, nonblank, progress_marker, project_files,
    split_body,
)

ORIGIN_URL = "https://github.com/o/r"
# Contract C: the one gh call that reads the notes.
NOTES_ARGS = ["issue", "list", "--state", "all", "--limit", "300", "--json",
              "number,body,comments"]
# Contract C: the last sentence of the block, by task.
IF_SENTENCE = ("Take each note into the design where it applies, and say in your report which "
               "ones you did not take, and why.")
DV2_SENTENCE = ("Where a note differs from the approved design, follow the design and say so in "
                "your report.")
DISABLED = "the 'ZJUCao/wordcount' repository has disabled issues"
BAD_GATEWAY = "HTTP 502: Bad Gateway (https://api.github.com/graphql)"
CRASH = "Crash on empty history"
DOCS_DESIGN = "[docs] Update the F02 design"
DOCS_PLAN = "[docs] Add cases to the F02 test plan"
INPUT_TEXT = ("Code Reviewer review, round 1: changes-requested\n\n1. Name the option --lines.\n"
              "2. Count the last line.\n\n\n")
SAFE = re.compile(r"[A-Za-z0-9_./:=@%+,-]+")
THREE = (F01, F02, F03)


# ------------------------------------------------------------------ gh's answers

def at(day: int, hour: int, minute: int = 0) -> str:
    """A GitHub time stamp in November 2026."""
    return f"2026-11-{day:02d}T{hour:02d}:{minute:02d}:00Z"


def comment_url(issue: int, cid: int) -> str:
    """A comment's ``url``, for example ``.../issues/7#issuecomment-701``."""
    return f"{REPO_URL}/issues/{issue}#issuecomment-{cid}"


def comment(issue: int, cid: int, body: str, created: str, author: str = LOGIN) -> dict:
    """One comment of ``gh issue list --json comments``."""
    return {"author": {"login": author}, "body": body, "createdAt": created,
            "url": comment_url(issue, cid)}


def note_body(target: str, source: str, text: str) -> str:
    """A note comment's body (contract A)."""
    return f"Note for {target}, from {source}\n\n{text}\n"


def gh_issue(number: int, body: str, found: Sequence[Mapping], labels: Sequence[str],
             state: str = "OPEN", reason: Optional[str] = None,
             title: Optional[str] = None) -> dict:
    """One issue of ``gh issue list --state all``; a higher number is newer."""
    return {"number": number, "title": title or f"Issue {number}",
            "labels": [{"name": name} for name in labels], "body": body,
            "comments": [dict(c) for c in found], "url": f"{REPO_URL}/issues/{number}",
            "createdAt": f"2026-11-01T00:{number:02d}:00Z", "state": state,
            "stateReason": reason, "author": {"login": LOGIN}}


def progress(number: int, fid: str, found: Sequence[Mapping] = (), state: str = "OPEN",
             reason: Optional[str] = None, body: Optional[str] = None) -> dict:
    """A progress issue whose body is out of date: its marker and one old line."""
    text = body if body is not None else progress_marker(fid) + "\nOld text.\n"
    return gh_issue(number, text, found, ("progress",), state, reason, f"{fid} old title")


def gh_pr(number: int, title: str, state: str = "MERGED", created: str = "") -> dict:
    """One PR of ``gh pr list --state all``, with its ``createdAt``."""
    return {"number": number, "title": title, "state": state,
            "url": f"{REPO_URL}/pull/{number}",
            "createdAt": created or f"2026-11-01T00:{number % 60:02d}:00Z"}


def block(feature: str, notes: Sequence[tuple], sentence: str) -> str:
    """The notes block of contract C: the heading, each note, a blank line, and the sentence.

    Args:
        feature: The item, for example ``F02``.
        notes: ``(source, url, text)`` triples, oldest first.
        sentence: The task's last sentence.

    Returns:
        The block, without a newline at the end.
    """
    lines = [f"Notes for {feature} from earlier work, kept on its progress issues:"]
    for index, (source, url, text) in enumerate(notes, 1):
        lines.append(f"{index}. From {source} ({url}):")
        lines += [f"   {line}" if line else "" for line in text.split("\n")]
    return "\n".join(lines + ["", sentence])


# ------------------------------------------------------------------ clones

def base():
    """The first commit: features F01 to F05, with a Chinese mirror that has a table."""
    return base_step(project_files(FIVE))


def on_github(project: Project) -> Project:
    """Sets ``remote.origin.url`` to GitHub and maps it back to the bare origin."""
    project.git("config", "remote.origin.url", ORIGIN_URL)
    project.git("config", f"url.{project.origin.as_posix()}.insteadOf", ORIGIN_URL)
    return project


def github_clone(steps: Sequence) -> Project:
    """A clone on ``troy-mode/work`` whose configured origin is on GitHub."""
    return on_github(Project(steps))


class SpacedClone(Project):
    """A clone in a folder whose path holds a space, so its git folder does too."""

    def __init__(self, steps: Sequence) -> None:
        """Clones the origin built from the steps into ``<new folder>/with space/wordcount``."""
        self.origin = origin_repo(steps)
        self.tmp = new_dir("spaced") / "with space"
        self.tmp.mkdir()
        self.root = self.tmp / "wordcount"
        git(self.tmp, "clone", "-q", str(self.origin), "wordcount")
        self.git("switch", "-q", "-c", WORK_BRANCH, "origin/main")


def add_team(home: Path, name: str) -> Path:
    """Makes ``<home>/.troy-teams/<name>`` as ``team start`` does, and returns it."""
    common = Path(git(home, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    exclude = common / "info" / "exclude"
    text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text(text + ("" if not text or text.endswith("\n") else "\n")
                       + "/.troy-teams/\n", encoding="utf-8")
    path = home / ".troy-teams" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    git(home, "worktree", "add", "-q", "--detach", str(path), "origin/main")
    return path


def no_json_fakes() -> Fakes:
    """Fakes whose gh records each call and prints a page that is not JSON, with exit 0."""
    fakes = Fakes()
    log = fakes.folder / "gh_calls.jsonl"
    source = ("import json\nimport os\nimport sys\nfrom pathlib import Path\n\n"
              f"LOG = Path({str(log)!r})\n"
              "with LOG.open('a', encoding='utf-8') as handle:\n"
              "    handle.write(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}) + '\\n')\n"
              "sys.stdout.write('<html><body>Unicorn! This page is taking too long.</body>"
              "</html>\\n')\n"
              "sys.exit(0)\n")
    if os.name == "nt":
        (fakes.folder / "fake_gh.py").write_text(source, encoding="utf-8")
    else:
        (fakes.folder / "gh").write_text(f"#!{sys.executable}\n{source}", encoding="utf-8")
    return fakes


def calls_from(fakes, root: Path) -> list:
    """The argv of each gh call made in a folder, oldest first."""
    return [call["argv"] for call in fakes.gh_calls() if same_path(call["cwd"], root)]


def problem_texts(report: Mapping) -> list:
    """The report's problems as text."""
    return [p if isinstance(p, str) else str(p.get("message", p))
            for p in report.get("problems") or []]


def split_input(prompt: str) -> tuple:
    """Splits a prompt at its Input field.

    Returns:
        ``(text before, the Input text or None for "Input: None", text from Round on)``, or
        ``(None, None, None)`` when the prompt has no Input field before a Round line.
    """
    lines = prompt.split("\n")
    start = next((i for i, line in enumerate(lines) if line in ("Input:", "Input: None")), None)
    if start is None:
        return None, None, None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("Round: ")), None)
    if end is None:
        return None, None, None
    text = None if lines[start] == "Input: None" else "\n".join(lines[start + 1:end])
    if text is None and end != start + 1:
        return None, None, None
    return "\n".join(lines[:start]), text, "\n".join(lines[end:])


# ------------------------------------------------------------- briefs: data

def brief_issues() -> list:
    """Every issue the brief cases' fake gh serves: notes for F02 and F03, and comments that
    are no note. F02's issue is listed before F01's, so listing order is not time order."""
    f02 = [
        comment(8, 801, "Why does F02 wait?", at(2, 8)),
        comment(8, 802, "Note for F02, from Troy, in chat\r\n\r\nShow 行数 in the summary "
                        "line.\r\n", at(5, 9)),
        comment(8, 803, "Note for F02 from Troy, in chat\n\nNo comma: no note.", at(5, 9, 30)),
        comment(8, 804, "Re: Note for F02, from Troy, in chat\n\nNot first: no note.",
                at(5, 9, 40)),
        comment(8, 805, "note for F02, from Troy, in chat\n\nLower case: no note.", at(5, 9, 50)),
        comment(8, 806, note_body("F020", "Troy, in chat", "F020's own note."), at(5, 10)),
        comment(8, 807, note_body("F03", "Troy, in chat", "F03 counts characters, not bytes."),
                at(5, 10, 10)),
        comment(8, 810, "Note for F2, from Troy, in chat\n\nOne digit: no note.", at(5, 10, 20)),
        comment(8, 811, "Note for F02, from\n\nNo source: no note.", at(5, 10, 30)),
        comment(8, 808, note_body("F02", "Troy, in chat", "Name the option --lines."), at(6, 8)),
        comment(8, 809, note_body("F02", "#12, Architect, round 1", "Read F01's design first."),
                at(6, 8)),
    ]
    f01 = [
        comment(7, 701, "Note for F02, from #46, Code Reviewer, round 1\n\n\nCount the last "
                        "line even when the file has no final newline.\n\nF01's reader keeps "
                        "each carriage return.\n\n\n", at(3, 10)),
        comment(7, 702, note_body("F03", "#46, Code Reviewer, round 1", "F03 reads F01's "
                                                                        "tokens."), at(4, 10)),
        comment(7, 703, note_body("F02", "#46, Code Reviewer, round 2",
                                  "Keep the totals as integers."), at(6, 8), "reviewer-bot"),
    ]
    return [
        progress(8, "F02", f02),
        progress(7, "F01", f01, "CLOSED", "COMPLETED"),
        gh_issue(9, "Count tabs too.", [comment(9, 901, note_body(
            "F02", "Troy, in chat", "On an idea: no note."), at(4, 11))], ("idea",)),
        gh_issue(10, "Crash on empty history.", [comment(10, 1001, note_body(
            "F02", "Troy, in chat", "On a bug issue: no note."), at(4, 12))], ("bug",)),
        gh_issue(13, "Copied text.\n" + progress_marker("F02") + "\n", [comment(13, 1301, note_body(
            "F02", "Troy, in chat", "Marker not on the first line: no note."), at(4, 13))],
                 ("progress",)),
        progress(14, "F05", [comment(14, 1401, note_body("F03", "Troy, in chat",
                                                         "F03 shows a total line."), at(7, 8))],
                 "CLOSED", "NOT_PLANNED"),
    ]


# F02's notes, oldest first: A on closed #7, B with CRLF on #8, then C, D, and E at one time:
# C first by issue number, then D and E in comment order (E's source sorts before D's).
F02_NOTES = (
    ("#46, Code Reviewer, round 1", comment_url(7, 701),
     "Count the last line even when the file has no final newline.\n\n"
     "F01's reader keeps each carriage return."),
    ("Troy, in chat", comment_url(8, 802), "Show 行数 in the summary line."),
    ("#46, Code Reviewer, round 2", comment_url(7, 703), "Keep the totals as integers."),
    ("Troy, in chat", comment_url(8, 808), "Name the option --lines."),
    ("#12, Architect, round 1", comment_url(8, 809), "Read F01's design first."),
)
F03_NOTES = (
    ("#46, Code Reviewer, round 1", comment_url(7, 702), "F03 reads F01's tokens."),
    ("Troy, in chat", comment_url(8, 807), "F03 counts characters, not bytes."),
    ("Troy, in chat", comment_url(14, 1401), "F03 shows a total line."),
)
NOT_NOTES = ("No comma: no note.", "Not first: no note.", "Lower case: no note.",
             "F020's own note.", "One digit: no note.", "No source: no note.",
             "On an idea: no note.", "On a bug issue: no note.",
             "Marker not on the first line: no note.", "Why does F02 wait?")

STATE_STEPS = {
    "s1": [base(), *stages(F01, 6)],
    "s2": [base(), *stages(F01, 6), *stages(F02, 1)],
    "s3": [base(), *stages(F01, 6), *stages(F02, 2), bug_step("B12", "test", CRASH)],
    "s4": [base(), *stages(F01, 6), *stages(F02, 3)],
    "s5": [base(), *stages(F01, 6), *stages(F02, 4)],
    "rework": [base(), *stages(F01, 6), *stages(F02, 5),
               change_step(features=(F01, rework(F02), F03, F04, F05))],
}

# (label, state, task, item, --title, --round, with an Input file, feature, sentence)
NOTE_CASES = [
    ("IF1 at PR 1 without Input", "s1", "IF1", "F02", None, None, False, "F02", IF_SENTENCE),
    ("IF1 at PR 1 with Input", "s1", "IF1", "F02", None, None, True, "F02", IF_SENTENCE),
    ("IF2 at PR 1, round 2", "s1", "IF2", "F02", None, 2, True, "F02", IF_SENTENCE),
    ("IF1 at PR 1 for F03", "s1", "IF1", "F03", None, None, False, "F03", IF_SENTENCE),
    ("IF2 in a [docs] side PR", "s3", "IF2", "F02", DOCS_DESIGN, None, True, "F02",
     IF_SENTENCE),
    ("DV2 at PR 5 without Input", "s5", "DV2", "F02", None, None, False, "F02", DV2_SENTENCE),
    ("DV2 at PR 5, round 2", "s5", "DV2", "F02", None, 2, True, "F02", DV2_SENTENCE),
    ("IF1 on the redo of PR 1", "rework", "IF1", "F02", F02.title(1), None, True, "F02",
     IF_SENTENCE),
    ("IF2 on the redo of PR 1, round 2", "rework", "IF2", "F02", F02.title(1), 2, True, "F02",
     IF_SENTENCE),
    ("DV2 on the redo of PR 5", "rework", "DV2", "F02", F02.title(5), None, False, "F02",
     DV2_SENTENCE),
]
# (label, state, task, item, --title, --round, with an Input file)
OLD_CASES = [
    ("AR2 at PR 1", "s1", "AR2", "F02", None, None, True),
    ("AR5 at PR 1", "s1", "AR5", "F02", None, None, True),
    ("IF1 at PR 1 for F04, which has no note", "s1", "IF1", "F04", None, None, True),
    ("IF1 at PR 1 for F04 without Input", "s1", "IF1", "F04", None, None, False),
    ("TM5 for bug B12", "s1", "TM5", "B12", None, None, True),
    ("TM7 for v0.1", "s1", "TM7", "v0.1", None, None, False),
    ("TM1 at PR 2", "s2", "TM1", "F02", None, None, False),
    ("IF3 at PR 2", "s2", "IF3", "F02", None, None, True),
    ("DV1 at PR 3", "s3", "DV1", "F02", None, None, False),
    ("CR1 at PR 3", "s3", "CR1", "F02", None, None, False),
    ("TM1 in a [docs] side PR", "s3", "TM1", "F02", DOCS_PLAN, None, True),
    ("AR2 in a [docs] side PR", "s3", "AR2", "F02", DOCS_DESIGN, None, True),
    ("IF3 in a [docs] side PR", "s3", "IF3", "F02", DOCS_DESIGN, None, True),
    ("DV3 for bug B12", "s3", "DV3", "B12", None, None, False),
    ("CR1 for bug B12", "s3", "CR1", "B12", None, None, False),
    ("TE1 at PR 4", "s4", "TE1", "F02", None, None, False),
    ("TM2 at PR 4", "s4", "TM2", "F02", None, None, False),
    ("CR1 at PR 5", "s5", "CR1", "F02", None, None, False),
    ("TM3 at PR 5", "s5", "TM3", "F02", None, None, True),
    ("IF4 at PR 5", "s5", "IF4", "F02", None, None, True),
    ("DV1 on the redo of PR 3", "rework", "DV1", "F02", F02.title(3), None, False),
    ("CR1 on the redo of PR 5", "rework", "CR1", "F02", F02.title(5), None, False),
]
_SHARED: dict = {}


def input_file() -> Path:
    """The Input file every case with Input uses, written once."""
    if "input" not in _SHARED:
        folder = new_dir("input")
        write_file(folder, "input.md", INPUT_TEXT)
        _SHARED["input"] = folder / "input.md"
    return _SHARED["input"]


def brief_args(task: str, item: str, title: Optional[str], round_: Optional[int],
               with_input: bool) -> list:
    """The ``brief`` options of one case."""
    args = ["brief", "--task", task, "--item", item]
    if title is not None:
        args += ["--title", title]
    if round_ is not None:
        args += ["--round", str(round_)]
    if with_input:
        args += ["--input-file", str(input_file())]
    return args


def pairs() -> dict:
    """Each state's GitHub clone and its twin with a local origin, built once."""
    if "pairs" not in _SHARED:
        _SHARED["pairs"] = {name: (github_clone(steps), Project(steps))
                            for name, steps in STATE_STEPS.items()}
    return _SHARED["pairs"]


def brief_runs() -> dict:
    """Runs every case's brief on its GitHub clone and its twin, with one set of fakes each.

    Returns:
        The label mapped to ``(GitHub outcome, twin outcome, fakes, GitHub clone, twin)``.
    """
    if "runs" not in _SHARED:
        built = pairs()
        input_file()
        cases = [(c[0], c[1], brief_args(*c[2:7])) for c in NOTE_CASES + OLD_CASES]
        fakes = {label: Fakes(all_issues=brief_issues()) for label, _, _ in cases}

        def run(case):
            """Runs one case on both clones, the GitHub clone first."""
            label, state, args = case
            hub, twin = built[state]
            return (hub.run(*args, fakes=fakes[label]), twin.run(*args, fakes=fakes[label]),
                    fakes[label], hub, twin)
        _SHARED["runs"] = dict(zip([c[0] for c in cases], parallel(run, cases)))
    return _SHARED["runs"]


class NotesCase(FlowCase):
    """Assertions shared by the brief tests."""

    def brief_report(self, out: Outcome, label: str) -> dict:
        """A brief's report, which must have exit 0 and a prompt."""
        report = self.report_of(out, 0, "brief")
        self.assertIsInstance(report.get("prompt"), str, f"{label}: {out.describe()}")
        return report

    def parts(self, prompt: str, label: str) -> tuple:
        """A prompt split at its Input field, which it must have."""
        found = split_input(prompt)
        self.assertIsNotNone(found[0], f"{label}: no Input field before Round:\n{prompt}")
        return found

    def assert_old_input(self, report: dict, with_input: bool, label: str) -> None:
        """The twin's brief keeps the old Input: the file's text right-stripped, or None."""
        _, text, _ = self.parts(report["prompt"], label)
        want = INPUT_TEXT.rstrip() if with_input else None
        self.assertEqual(text, want, f"{label}: the twin's Input\n{report['prompt']}")
        self.assertNotIn("Notes for ", report["prompt"], label)
        self.assertEqual(report.get("input"), INPUT_TEXT if with_input else None, label)

    def assert_brief_with(self, hub: Outcome, twin: Outcome, combined: str, label: str) -> None:
        """The GitHub brief equals the twin's with only its Input field set to ``combined``."""
        got = self.brief_report(hub, label)
        ref = self.brief_report(twin, label)
        before, text, after = self.parts(got["prompt"], label)
        ref_before, _, ref_after = self.parts(ref["prompt"], label)
        self.assertEqual(text, combined, f"{label}: the Input field")
        self.assertEqual(before, ref_before, f"{label}: the prompt before Input")
        self.assertEqual(after, ref_after, f"{label}: the prompt from Round on")
        self.assertIsInstance(got.get("input"), str, label)
        self.assertEqual(got["input"].rstrip(), combined, f"{label}: the report's input")
        for key, value in ref.items():
            if key not in ("prompt", "input"):
                self.assertEqual(got.get(key), value, f"{label}: report key {key}")


# ---------------------------------------------------------------- C: briefs

class BriefNotesTests(NotesCase):
    """IF1, IF2, and DV2 of a feature get its notes in Input (contract A and C)."""

    @classmethod
    def setUpClass(cls):
        """Runs every brief case once."""
        cls.runs = brief_runs()

    def expected(self, case: tuple) -> str:
        """The case's combined Input: the file's text right-stripped and a blank line, then
        the block; or the block alone."""
        notes = F02_NOTES if case[7] == "F02" else F03_NOTES
        text = block(case[7], notes, case[8])
        return INPUT_TEXT.rstrip() + "\n\n" + text if case[6] else text

    def test_each_brief_holds_its_block(self):
        """The exact block after the Input file's text or alone, and the task's sentence; the
        rest of the brief and of its report as the twin's."""
        for case in NOTE_CASES:
            with self.subTest(case=case[0]):
                hub, twin = self.runs[case[0]][:2]
                self.assert_brief_with(hub, twin, self.expected(case), case[0])

    def test_twin_keeps_the_old_input(self):
        """The reference itself: the twin's Input is the old one, so the comparison above
        cannot hide a change that reaches every brief."""
        for case in NOTE_CASES:
            with self.subTest(case=case[0]):
                report = self.brief_report(self.runs[case[0]][1], case[0])
                self.assert_old_input(report, case[6], case[0])

    def test_one_gh_call_in_the_repository(self):
        """Exactly one gh call, ``gh issue list --state all --limit 300 --json
        number,body,comments``, made in the GitHub clone's folder."""
        for case in NOTE_CASES:
            with self.subTest(case=case[0]):
                _, _, fakes, hub, _ = self.runs[case[0]]
                self.assertEqual(calls_from(fakes, hub.root), [NOTES_ARGS])

    def test_twin_makes_no_gh_call(self):
        """An origin that is a local folder: no gh call at all."""
        for case in NOTE_CASES + OLD_CASES:
            with self.subTest(case=case[0]):
                _, _, fakes, _, twin = self.runs[case[0]]
                self.assertEqual(calls_from(fakes, twin.root), [])

    def test_oldest_first_with_ties(self):
        """By ``createdAt``; at one time, by issue number, then by comment order."""
        prompt = self.brief_report(self.runs[NOTE_CASES[0][0]][0], NOTE_CASES[0][0])["prompt"]
        found = re.findall(r"^\d+\. From .* \((\S+)\):$", prompt, re.M)
        self.assertEqual(found, [url for _, url, _ in F02_NOTES], prompt)

    def test_note_on_a_closed_progress_issue_counts(self):
        """F01's issue #7 is closed: its notes for F02 are in F02's block."""
        prompt = self.brief_report(self.runs[NOTE_CASES[0][0]][0], NOTE_CASES[0][0])["prompt"]
        for cid in (701, 703):
            with self.subTest(comment=cid):
                self.assertIn(f"({comment_url(7, cid)}):", prompt)

    def test_only_the_items_notes(self):
        """F02's briefs hold none of F03's notes, F03's none of F02's, and no brief holds a
        comment that is no note."""
        for case in NOTE_CASES:
            with self.subTest(case=case[0]):
                prompt = self.brief_report(self.runs[case[0]][0], case[0])["prompt"]
                others = F03_NOTES if case[7] == "F02" else F02_NOTES
                for _, url, text in others:
                    self.assertNotIn(url, prompt)
                    self.assertNotIn(text, prompt)
                for text in NOT_NOTES:
                    self.assertNotIn(text, prompt)

    def test_text_lines_are_indented_and_crlf_is_read_as_lf(self):
        """Three spaces before each text line, an empty text line stays empty, no CR."""
        prompt = self.brief_report(self.runs[NOTE_CASES[0][0]][0], NOTE_CASES[0][0])["prompt"]
        self.assertIn("1. From #46, Code Reviewer, round 1 (" + comment_url(7, 701) + "):\n"
                      "   Count the last line even when the file has no final newline.\n\n"
                      "   F01's reader keeps each carriage return.\n2. From ", prompt)
        self.assertIn("   Show 行数 in the summary line.\n3. From ", prompt)
        self.assertNotIn("\r", prompt)


class BriefWithoutNotesTests(NotesCase):
    """Every other task, a bug, a version, and a feature without notes: the old brief."""

    @classmethod
    def setUpClass(cls):
        """Runs every brief case once."""
        cls.runs = brief_runs()

    def test_other_tasks_get_the_old_brief(self):
        """The GitHub clone's report equals the twin's, the prompt byte for byte."""
        for case in OLD_CASES:
            with self.subTest(case=case[0]):
                hub, twin = self.runs[case[0]][:2]
                got = self.brief_report(hub, case[0])
                ref = self.brief_report(twin, case[0])
                self.assertEqual(got["prompt"], ref["prompt"])
                self.assertEqual(got, ref)
                self.assertNotIn("Notes for ", got["prompt"])

    def test_twin_keeps_the_old_input(self):
        """The reference itself has the old Input."""
        for case in OLD_CASES:
            with self.subTest(case=case[0]):
                report = self.brief_report(self.runs[case[0]][1], case[0])
                self.assert_old_input(report, case[6], case[0])


class OriginTests(NotesCase):
    """Only a configured ``remote.origin.url`` that holds ``github.com`` reads notes (C)."""

    @classmethod
    def setUpClass(cls):
        """F02's IF1 on a GitLab origin and on a local origin that insteadOf rewrites to
        GitHub, each beside a twin, with one set of fakes each."""
        steps = STATE_STEPS["s1"]
        gitlab = Project(steps)
        gitlab.git("config", "remote.origin.url", "https://gitlab.com/o/r")
        gitlab.git("config", f"url.{gitlab.origin.as_posix()}.insteadOf", "https://gitlab.com/o/r")
        rewritten = Project(steps)
        local = rewritten.git("config", "--get", "remote.origin.url").strip()
        rewritten.git("config", f"url.{ORIGIN_URL}.insteadOf", local)
        twin = pairs()["s1"][1]
        args = brief_args("IF1", "F02", None, None, True)

        def run(project):
            """Runs the brief on one clone and on the twin with the same fakes."""
            fakes = Fakes(all_issues=brief_issues())
            return project.run(*args, fakes=fakes), twin.run(*args, fakes=fakes), fakes
        cls.clones = {"GitLab": gitlab, "rewritten to GitHub": rewritten}
        cls.outs = dict(zip(cls.clones, parallel(run, list(cls.clones.values()))))

    def test_old_brief_and_no_gh_call(self):
        """No gh call at all, and the twin's brief byte for byte. For the second clone,
        ``git remote get-url origin`` names GitHub while the configured value does not."""
        rewritten = self.clones["rewritten to GitHub"]
        self.assertEqual(rewritten.git("remote", "get-url", "origin").strip(), ORIGIN_URL)
        self.assertNotIn("github.com", rewritten.git("config", "--get", "remote.origin.url"))
        for name in self.clones:
            with self.subTest(origin=name):
                out, twin_out, fakes = self.outs[name]
                self.assertEqual(fakes.gh_argvs(), [])
                got = self.brief_report(out, name)
                self.assertEqual(got, self.brief_report(twin_out, name))
                self.assertNotIn("Notes for ", got["prompt"])


class GhFailureTests(NotesCase):
    """gh cannot read the issues on a GitHub origin (contract C)."""

    @classmethod
    def setUpClass(cls):
        """F02's IF1 with gh failing, printing no JSON, and saying issues are disabled."""
        steps = STATE_STEPS["s1"]
        args = brief_args("IF1", "F02", None, None, True)
        cases = {
            "fails": Fakes(all_issues=brief_issues(),
                           fail_on=[(["issue", "list", "--state", "all"], BAD_GATEWAY)]),
            "no JSON": no_json_fakes(),
            "disabled": Fakes(all_issues=brief_issues(), issues_enabled=False,
                              fail_on=[(["issue", "list", "--state", "all"], DISABLED)]),
        }
        cls.clones = {name: github_clone(steps) for name in cases}
        cls.twin = Project(steps)
        cls.fakes = cases

        def run(name):
            """Runs the brief on the case's GitHub clone, then on the twin."""
            return (cls.clones[name].run(*args, fakes=cases[name]),
                    cls.twin.run(*args, fakes=cases[name]))
        cls.outs = dict(zip(cases, parallel(run, list(cases))))

    def assert_stopped(self, name: str) -> None:
        """Exit 1, a problem that says F02's notes could not be read, and no prompt."""
        out = self.outs[name][0]
        report = self.report_of(out, 1, "brief")
        self.assertFalse(report.get("prompt"), out.describe())
        found = [p for p in problem_texts(report)
                 if re.search(r"(?i)notes of F02 could not be read from GitHub", p)]
        self.assertEqual(len(found), 1, report.get("problems"))
        self.assertEqual(calls_from(self.fakes[name], self.clones[name].root), [NOTES_ARGS])

    def test_failing_gh_stops_the_brief(self):
        """gh exits 1: exit 1, the problem, and no prompt."""
        self.assert_stopped("fails")

    def test_no_json_stops_the_brief(self):
        """gh exits 0 but prints no JSON: the same."""
        self.assert_stopped("no JSON")

    def test_disabled_issues_count_as_no_notes(self):
        """GitHub's "disabled issues": exit 0 and the old brief byte for byte."""
        got = self.brief_report(self.outs["disabled"][0], "disabled")
        self.assertEqual(got, self.brief_report(self.outs["disabled"][1], "disabled"))


class TeamBriefTests(NotesCase):
    """A team's brief reads the notes through gh in its worktree (F07 design 6.6, F20)."""

    @classmethod
    def setUpClass(cls):
        """F02's IF1 from the team worktree f02 of a GitHub home checkout, and from the home."""
        cls.home = github_clone(STATE_STEPS["s1"])
        cls.worktree = add_team(cls.home.root, "f02")
        cls.fakes = Fakes(all_issues=brief_issues())
        args = brief_args("IF1", "F02", None, None, True)
        neutral = new_dir("neutral")
        cls.team_out = run_engine([*args, "--repo", cls.worktree, "--json"], neutral, cls.fakes)
        cls.home_out = cls.home.run(*args, fakes=cls.fakes)
        cls.combined = INPUT_TEXT.rstrip() + "\n\n" + block("F02", F02_NOTES, IF_SENTENCE)

    def test_team_brief_holds_the_notes(self):
        """The team's brief is a team brief, and its Input holds F02's block."""
        report = self.brief_report(self.team_out, "team")
        self.assertIn("team", report, self.team_out.describe())
        self.assertEqual(self.parts(report["prompt"], "team")[1], self.combined)

    def test_home_brief_holds_the_same_notes(self):
        """The home checkout's brief holds the same Input."""
        report = self.brief_report(self.home_out, "home")
        self.assertEqual(self.parts(report["prompt"], "home")[1], self.combined)

    def test_gh_runs_in_the_worktree(self):
        """The team's brief made its one gh call in the worktree, the home's in the home."""
        self.assertEqual(calls_from(self.fakes, self.worktree), [NOTES_ARGS])
        self.assertEqual(calls_from(self.fakes, self.home.root), [NOTES_ARGS])


# ------------------------------------------------------------------ B: note

TEXT = "\n\nF03 groups recipes by equality of their names, not by identity.\nSecond line: 字符.\n\n \n"
STRIPPED = "F03 groups recipes by equality of their names, not by identity.\nSecond line: 字符."
NOTE_STEPS = [base(), *stages(F01, 6), *stages(F02, 2)]


def note_prs() -> list:
    """The PRs ``gh pr list --state all`` gives the note cases."""
    return ([gh_pr(41 + i, F01.title(1 + i)) for i in range(6)]
            + [gh_pr(51, F02.title(1)), gh_pr(52, F02.title(2)),
               gh_pr(53, "[F02 test-fix] Wrong count in F02-T01", "OPEN"),
               gh_pr(57, f"[B12 A/B test] {CRASH}", "OPEN"),
               gh_pr(58, "[docs] Release v0.1.0", "CLOSED"),
               gh_pr(60, F05.title(1), "CLOSED")])


def note_issues(with_f02: bool = True, with_f03: bool = True) -> list:
    """F01's two closed issues, F02's open and closed ones, F03's open one, and an idea."""
    found = [progress(7, "F01", (), "CLOSED", "COMPLETED"),
             progress(12, "F01", (), "CLOSED", "COMPLETED")]
    if with_f02:
        found += [progress(8, "F02"), progress(20, "F02", (), "CLOSED", "NOT_PLANNED")]
    if with_f03:
        found.append(progress(9, "F03"))
    found.append(gh_issue(30, "Count tabs too.", (), ("idea",)))
    return found


def note_fakes(**more) -> Fakes:
    """Fakes for a note case: the note PRs and issues, overridden by ``more``."""
    return Fakes(**{"all_prs": note_prs(), "all_issues": note_issues(), **more})


def text_file(text: str) -> Path:
    """A new file that holds a note's text in UTF-8."""
    folder = new_dir("notetext")
    write_file(folder, "note.md", text)
    return folder / "note.md"


def git_state(project: Project) -> tuple:
    """HEAD, the refs, and the working tree's status, to see that nothing changed."""
    return (project.head(), project.git("for-each-ref"), project.status_lines(),
            project.git("stash", "list"))


def notes_dir(project: Project) -> Path:
    """``<git dir>/troy-mode/flow/notes``."""
    return project.git_dir() / "troy-mode" / "flow" / "notes"


def state_files(project: Project) -> list:
    """Every file under ``<git dir>/troy-mode``, as paths relative to it."""
    root = project.git_dir() / "troy-mode"
    if not root.is_dir():
        return []
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def note_run(project: Project, target: str, source: str, text: str, fakes: Fakes) -> tuple:
    """Runs ``note --for <target> --from <source> --file <file> --json``.

    Returns:
        ``(outcome, git state before, git state after)``.
    """
    before = git_state(project)
    out = project.run("note", "--for", target, "--from", source, "--file", text_file(text),
                      fakes=fakes)
    return out, before, git_state(project)


# label: (--for, --from, the issue it goes on)
ISSUE_CASES = {
    "a stage PR's feature": ("F03", "#41, Code Reviewer, round 1", 12),
    "a side PR's feature": ("F04", "#53, Code Reviewer, round 2", 8),
    "a bug PR: the target's": ("F03", "#57, Test Engineer, round 1", 9),
    "a [docs] PR: the target's": ("F03", "#58, Code Reviewer, round 1", 9),
    "from chat: the target's": ("F03", "Troy, in chat", 9),
    "a source without an issue: the target's": ("F03", "#60, Architect, round 1", 9),
    "a PR gh does not list: the target's": ("F03", "#99, Code Reviewer, round 1", 9),
    "no target issue: the next feature's": ("F04", "Troy, in chat", 8),
    "no source or target issue: the next feature's": ("F05", "#60, Architect, round 1", 8),
}


class NoteCase(FlowCase):
    """Assertions shared by the ``note`` tests."""

    def assert_nothing_else(self, project: Project, fakes: Fakes, before: tuple,
                            after: tuple) -> None:
        """No git write, no GitHub write, and no file under ``<git dir>/troy-mode`` outside
        ``flow/notes``."""
        self.assertEqual(after, before, "the run changed git")
        for argv in fakes.gh_argvs():
            with self.subTest(argv=argv):
                self.assertIn(tuple(argv[:2]), READ_CALLS, f"a gh call that writes: {argv}")
        for rel in state_files(project):
            with self.subTest(file=rel):
                self.assertTrue(rel.startswith("flow/notes/"), rel)

    def assert_note(self, out: Outcome, project: Project, target: str, source: str,
                    issue: int, text: str = STRIPPED) -> dict:
        """Exit 0, the report's fields, the file's exact body and place, and the command."""
        report = self.report_of(out, 0, "note")
        self.assertEqual((report.get("target"), report.get("source"), report.get("issue")),
                         (target, source, issue), out.describe())
        path = report.get("file")
        self.assertIsInstance(path, str, out.describe())
        self.assertTrue(Path(path).is_absolute(), path)
        self.assertTrue(same_path(Path(path).parent, notes_dir(project)), path)
        self.assertEqual(Path(path).read_bytes(),
                         f"Note for {target}, from {source}\n\n{text}\n".encode("utf-8"))
        self.assert_command(report, issue)
        return report

    def assert_command(self, report: dict, issue: int) -> None:
        """``gh issue comment <n> --body-file <file>``, the path quoted when it must be."""
        path, command = report["file"], report.get("gh")
        self.assertIsInstance(command, str, report)
        if SAFE.fullmatch(path):
            self.assertEqual(command, f"gh issue comment {issue} --body-file {path}")
        self.assertEqual(shlex.split(command),
                         ["gh", "issue", "comment", str(issue), "--body-file", path], command)


class NoteIssueTests(NoteCase):
    """Which progress issue a note goes on (contract B), and what ``note`` writes."""

    @classmethod
    def setUpClass(cls):
        """Runs each case on its own clone with its own fakes."""
        def run(label):
            """One case's run."""
            target, source, _ = ISSUE_CASES[label]
            project, fakes = github_clone(NOTE_STEPS), note_fakes()
            return (*note_run(project, target, source, TEXT, fakes), project, fakes)
        cls.outs = dict(zip(ISSUE_CASES, parallel(run, list(ISSUE_CASES))))

    def test_issue_choice(self):
        """The source feature's issue from a stage or side PR title, else the target's, else
        the next feature's; a feature's open issue before its newest closed one."""
        for label, (target, source, issue) in ISSUE_CASES.items():
            with self.subTest(case=label):
                out, _, _, project, _ = self.outs[label]
                self.assert_note(out, project, target, source, issue)

    def test_open_issue_before_a_newer_closed_one(self):
        """F02 has open #8 and closed #20: #8. F01 has closed #7 and #12: #12."""
        self.assertEqual(self.outs["a side PR's feature"][0].report.get("issue"), 8)
        self.assertEqual(self.outs["a stage PR's feature"][0].report.get("issue"), 12)

    def test_nothing_else_changes(self):
        """No git write, no GitHub write, nothing else under the git folder."""
        for label in ISSUE_CASES:
            with self.subTest(case=label):
                out, before, after, project, fakes = self.outs[label]
                self.assert_exit(out, 0)
                self.assert_nothing_else(project, fakes, before, after)

    def test_reads_the_pr_titles_from_gh(self):
        """A ``#<n>`` source reads ``gh pr list --state all``."""
        _, _, _, _, fakes = self.outs["a stage PR's feature"]
        self.assertIn(["pr", "list", "--state", "all"], [a[:4] for a in fakes.gh_argvs()])


class NoteFileTests(NoteCase):
    """Each note is a new file, and a path with a space is quoted (contract B)."""

    def test_each_note_is_a_new_file(self):
        """Two notes: two files; the first keeps its text."""
        project, fakes = github_clone(NOTE_STEPS), note_fakes()
        first = note_run(project, "F03", "Troy, in chat", TEXT, fakes)[0]
        report = self.assert_note(first, project, "F03", "Troy, in chat", 9)
        second = note_run(project, "F04", "#41, Code Reviewer, round 1", "Another note.",
                          fakes)[0]
        again = self.assert_note(second, project, "F04", "#41, Code Reviewer, round 1", 12,
                                 "Another note.")
        self.assertFalse(same_path(report["file"], again["file"]))
        self.assertEqual(Path(report["file"]).read_bytes(),
                         f"Note for F03, from Troy, in chat\n\n{STRIPPED}\n".encode("utf-8"))

    def test_path_with_a_space_is_quoted(self):
        """A git folder whose path holds a space: the command quotes the file for a shell."""
        project = on_github(SpacedClone(NOTE_STEPS))
        out, before, after = note_run(project, "F03", "Troy, in chat", TEXT, note_fakes())
        report = self.assert_note(out, project, "F03", "Troy, in chat", 9)
        self.assertIn(" ", report["file"])
        self.assertNotEqual(report["gh"], f"gh issue comment 9 --body-file {report['file']}")
        self.assertEqual(after, before)


class NoteOriginMainTests(NoteCase):
    """The features table and the accept stage come from origin/main, not the branch (B)."""

    @classmethod
    def setUpClass(cls):
        """A branch that adds F06 to the table, and one with F03's accept commit, neither on
        origin/main."""
        def run(kind):
            """Commits on the work branch, then runs one note."""
            project, fakes = github_clone(NOTE_STEPS), note_fakes()
            if kind == "added on the branch":
                project.commit("[docs] Add F06", {REQUIREMENTS: requirements_text(
                    (*FIVE, Feature("F06", "Sort the output")))})
                return note_run(project, "F06", "Troy, in chat", TEXT, fakes)[0], project
            project.commit(F03.title(6), {f"{F03.folder}/acceptance.md": "# F03 accepted\n"})
            return note_run(project, "F03", "Troy, in chat", TEXT, fakes)[0], project
        kinds = ("added on the branch", "accepted on the branch")
        cls.outs = dict(zip(kinds, parallel(run, kinds)))

    def test_feature_only_on_the_branch_is_unknown(self):
        """F06 is in the branch's table only: refused, and no file written."""
        out, project = self.outs["added on the branch"]
        report = self.report_of(out, 1, "note")
        self.assertTrue([p for p in problem_texts(report) if "F06" in p], out.describe())
        self.assertEqual(state_files(project), [])

    def test_accept_only_on_the_branch_is_not_accepted(self):
        """F03's accept commit is on the branch only: the note is written on F03's issue."""
        out, project = self.outs["accepted on the branch"]
        self.assert_note(out, project, "F03", "Troy, in chat", 9)


class NoteRefusalTests(NoteCase):
    """``note`` refuses with exit 1, writes nothing, and changes nothing (contract B)."""

    CASES = {
        "unknown": ("F09", TEXT, {}),
        "accepted": ("F01", TEXT, {}),
        "empty": ("F03", "", {}),
        "white space": ("F03", "  \n\n\t \n", {}),
        "no issue": ("F04", TEXT, {"all_issues": note_issues(with_f02=False)}),
        "turned off": ("F03", TEXT, {"issues_enabled": False, "fail_on": [
            (["issue", "list", "--state", "all"], DISABLED)]}),
    }

    @classmethod
    def setUpClass(cls):
        """Runs each refusal on its own clone, from chat."""
        def run(label):
            """One case's run."""
            target, text, more = cls.CASES[label]
            project, fakes = github_clone(NOTE_STEPS), note_fakes(**more)
            return (*note_run(project, target, "Troy, in chat", text, fakes), project, fakes)
        cls.outs = dict(zip(cls.CASES, parallel(run, list(cls.CASES))))

    def problems(self, label: str) -> list:
        """The case's problems; exit 1, nothing written, nothing changed."""
        out, before, after, project, fakes = self.outs[label]
        report = self.report_of(out, 1, "note")
        self.assertNotEqual(report["problems"], [], out.describe())
        self.assertEqual(state_files(project), [], "a file was written")
        self.assert_nothing_else(project, fakes, before, after)
        return problem_texts(report)

    def test_unknown_feature(self):
        """F09 is not in the features table: a problem that names it."""
        self.assertTrue([p for p in self.problems("unknown") if "F09" in p])

    def test_accepted_feature(self):
        """F01's accept stage merged: the problem says it is a requirement change (D65)."""
        found = [p for p in self.problems("accepted")
                 if "F01" in p and re.search(r"(?i)requirement change", p)]
        self.assertTrue(found, self.outs["accepted"][0].describe())

    def test_empty_text(self):
        """An empty file, and one of white space only."""
        for label in ("empty", "white space"):
            with self.subTest(case=label):
                self.problems(label)

    def test_no_progress_issue(self):
        """Neither the target nor the next feature has an issue: the problem says so."""
        found = [p for p in self.problems("no issue") if re.search(r"(?i)no progress issue", p)]
        self.assertTrue(found, self.outs["no issue"][0].describe())

    def test_issues_turned_off(self):
        """The repository has disabled issues: the problem says so."""
        found = [p for p in self.problems("turned off")
                 if re.search(r"(?i)turned off|disabled", p)]
        self.assertTrue(found, self.outs["turned off"][0].describe())


# ---------------------------------------------------------------- D: status

STATUS_STEPS = [base(), *stages(F01, 6), *stages(F02, 5), stage_step(F03, 1)]
NOTE_TEXTS = {"n1": "Before PR 1.", "n2": "At PR 1's opening.", "n3": "Late for the design.",
              "n4": "Late for both.", "m1": "After F03's PR 1.", "m2": "F04 has not started."}


def status_prs() -> list:
    """Every PR, with ``createdAt``: F02's first PR 1 closed unmerged, listed after the merged
    one; an earlier side PR of F02 and an earlier PR 1 of F020; F03's PR 1 merged, PR 2 open."""
    return ([gh_pr(41 + i, F01.title(1 + i), "MERGED", at(1, 1 + i)) for i in range(6)]
            + [gh_pr(47, "[F02 test-fix] Wrong count in F02-T01", "CLOSED", at(1, 7)),
               gh_pr(48, "[F020 1/6 design] Count other lines", "CLOSED", at(1, 8)),
               gh_pr(51, F02.title(1), "MERGED", at(2, 12)),
               gh_pr(50, F02.title(1), "CLOSED", at(2, 10)),
               gh_pr(52, F02.title(2), "MERGED", at(3, 10)),
               gh_pr(53, F02.title(3), "MERGED", at(3, 12)),
               gh_pr(54, F02.title(4), "MERGED", at(4, 8)),
               gh_pr(55, F02.title(5), "MERGED", at(4, 10)),
               gh_pr(60, F03.title(1), "MERGED", at(5, 10)),
               gh_pr(61, F03.title(2), "OPEN", at(6, 10))])


def status_issues() -> list:
    """Notes for F01 (accepted), F02, F03, F04, and F09 (not a feature), and one on an idea."""
    return [
        progress(7, "F01", [
            comment(7, 702, note_body("F02", "#51, Code Reviewer, round 1", NOTE_TEXTS["n3"]),
                    at(2, 11)),
            comment(7, 701, note_body("F01", "Troy, in chat", "Accepted already."), at(3, 0))],
                 "CLOSED", "COMPLETED"),
        progress(8, "F02", [
            comment(8, 801, note_body("F02", "Troy, in chat", NOTE_TEXTS["n1"]), at(2, 9)),
            comment(8, 802, note_body("F02", "#47, Code Reviewer, round 1", NOTE_TEXTS["n2"]),
                    at(2, 10)),
            comment(8, 803, note_body("F02", "#55, Code Reviewer, round 1", NOTE_TEXTS["n4"]),
                    at(4, 11)),
            comment(8, 804, note_body("F04", "Troy, in chat", NOTE_TEXTS["m2"]), at(5, 12)),
            comment(8, 805, note_body("F09", "Troy, in chat", "Not a feature."), at(5, 13))]),
        progress(9, "F03", [
            comment(9, 901, note_body("F03", "#60, Code Reviewer, round 1", NOTE_TEXTS["m1"]),
                    at(5, 11)),
            comment(9, 902, "Thanks for the update.", at(5, 14))]),
        gh_issue(30, "Count tabs too.", [comment(30, 3001, note_body(
            "F05", "Troy, in chat", "On an idea."), at(5, 15))], ("idea",)),
    ]


def status_fakes(**more) -> dict:
    """Fakes keyword arguments for the status cases; F03's open PR 2 has a note-like comment."""
    return {"prs": [stage_pr(61, F03, 2)],
            "comments": {61: comments(note_body("F04", "#61, Test Manager, round 1",
                                                "A PR comment is no note."))},
            "all_prs": status_prs(), "all_issues": status_issues(),
            "labels": list(ALL_LABELS), **more}


def entry(issue: int, cid: int, source: str, created: str, late: list) -> dict:
    """One note of ``feature_notes`` (contract D)."""
    return {"issue": issue, "url": comment_url(issue, cid), "source": source,
            "created": created, "late": late}


EXPECTED_FEATURE_NOTES = [
    {"id": "F02", "notes": [
        entry(8, 801, "Troy, in chat", at(2, 9), []),
        entry(8, 802, "#47, Code Reviewer, round 1", at(2, 10), []),
        entry(7, 702, "#51, Code Reviewer, round 1", at(2, 11), ["design"]),
        entry(8, 803, "#55, Code Reviewer, round 1", at(4, 11), ["design", "implementation"])]},
    {"id": "F03", "notes": [entry(9, 901, "#60, Code Reviewer, round 1", at(5, 11),
                                  ["design"])]},
    {"id": "F04", "notes": [entry(8, 804, "Troy, in chat", at(5, 12), [])]},
]


def status_case(more: Optional[Mapping] = None) -> tuple:
    """Runs ``status --json`` on a new clone of the status steps."""
    fakes = Fakes(**status_fakes(**(more or {})))
    project = Project(STATUS_STEPS)
    return project.run("status", fakes=fakes), fakes, project


class FeatureNotesTests(FlowCase):
    """``feature_notes`` and the messages for late notes (contract D)."""

    @classmethod
    def setUpClass(cls):
        """Runs status with readable issues, with a failing issue list, and with issues off."""
        cases = {"readable": None,
                 "unreadable": {"fail_on": [(["issue", "list", "--state", "all"], BAD_GATEWAY)]},
                 "turned off": {"issues_enabled": False,
                                "fail_on": [(["issue", "list", "--state", "all"], DISABLED)]}}
        cls.outs = dict(zip(cases, parallel(status_case, list(cases.values()))))

    def report(self, name: str) -> dict:
        """A case's status report."""
        return self.report_of(self.outs[name][0], 0, "status")

    def test_feature_notes(self):
        """One entry per feature not accepted with notes, in order, notes oldest first, each
        with its issue, link, source, time, and ``late``."""
        self.assertEqual(self.report("readable").get("feature_notes"), EXPECTED_FEATURE_NOTES)

    def test_no_entry_for_an_accepted_or_unknown_feature(self):
        """F01 is accepted and F09 is not a feature: no entry; an idea's comment and a PR
        comment are no note, so F05 has none and F04 only its one."""
        found = self.report("readable").get("feature_notes") or []
        self.assertEqual([e.get("id") for e in found], ["F02", "F03", "F04"])

    def test_late_design_counts_from_the_earliest_pr_1(self):
        """PR 1 opened with the closed #50: a note one hour later is late for the design, one
        at that very time is not, and the side PR and F020's PR do not count."""
        found = {e["id"]: e for e in self.report("readable").get("feature_notes") or []}
        lates = {n["url"]: n["late"] for n in found.get("F02", {}).get("notes", [])}
        self.assertEqual(lates.get(comment_url(7, 702)), ["design"])
        self.assertEqual(lates.get(comment_url(8, 802)), [])
        self.assertEqual(lates.get(comment_url(8, 801)), [])

    def test_a_line_for_each_late_note(self):
        """One message per late note, naming the feature, the source, the part it may have
        missed, and the link; none for a note that is not late."""
        messages = self.report("readable")["notes"]
        late = {comment_url(7, 702): ("F02", "#51, Code Reviewer, round 1", "design"),
                comment_url(8, 803): ("F02", "#55, Code Reviewer, round 1", "implementation"),
                comment_url(9, 901): ("F03", "#60, Code Reviewer, round 1", "design")}
        for url, words in late.items():
            with self.subTest(note=url):
                lines = [m for m in messages if url in m]
                self.assertEqual(len(lines), 1, messages)
                for word in words:
                    self.assertIn(word, lines[0])
        for cid in (801, 802, 804):
            with self.subTest(note=cid):
                self.assertFalse([m for m in messages if comment_url(8, cid) in m], messages)

    def test_pr_list_asks_for_created_at(self):
        """``gh pr list --state all`` asks for ``createdAt``."""
        calls = [a for a in self.outs["readable"][1].gh_argvs()
                 if a[:4] == ["pr", "list", "--state", "all"]]
        self.assertTrue(calls)
        for argv in calls:
            fields = (argv[argv.index("--json") + 1] if "--json" in argv else "").split(",")
            self.assertIn("createdAt", fields, argv)

    def test_unreadable_issues_give_no_notes(self):
        """An error or issues turned off: ``feature_notes`` is ``[]`` and status goes on."""
        for name in ("unreadable", "turned off"):
            with self.subTest(case=name):
                self.assertEqual(self.report(name).get("feature_notes"), [])


# --------------------------------------------------------- E: progress issues

E_STEPS = [base_step(project_files(THREE)), *stages(F01, 6), *stages(F02, 2)]
FINAL_F01 = progress_marker("F01") + "\n- [x] 6/6 验收：#46，已合并\n\nOld text.\n"
QUESTION = "Why does F02 wait?"


def e_fakes(issues: list) -> dict:
    """F02 at stage 3 is next; F03 has an open PR 1, so it gets a progress issue too."""
    return {"labels": list(ALL_LABELS), "prs": [stage_pr(61, F03, 1)],
            "all_prs": ([gh_pr(41 + i, F01.title(1 + i)) for i in range(6)]
                        + [gh_pr(51, F02.title(1)), gh_pr(52, F02.title(2)),
                           gh_pr(61, F03.title(1), "OPEN")]),
            "all_issues": issues}


def e_issues_with_notes() -> list:
    """F02's notes on closed #7 and open #8, out of number order in time; F03's on #8; and
    Troy's question on #8 before them."""
    return [
        progress(7, "F01", [comment(7, 701, note_body("F02", "#46, Code Reviewer, round 1",
                                                      "Count the last line."), at(4, 0))],
                 "CLOSED", "COMPLETED", FINAL_F01),
        progress(8, "F02", [
            comment(8, 800, QUESTION, at(3, 6)),
            comment(8, 801, note_body("F02", "Troy, in chat", "Name the option."), at(3, 8)),
            comment(8, 802, note_body("F03", "#52, Test Manager, round 1",
                                      "F03 counts characters."), at(3, 12)),
            comment(8, 803, note_body("F02", "Troy, in chat", "Show the total."), at(5, 0))]),
    ]


def e_issues_others_only() -> list:
    """F02's #8 holds only a note for F03."""
    return [progress(7, "F01", (), "CLOSED", "COMPLETED", FINAL_F01),
            progress(8, "F02", [comment(8, 802, note_body(
                "F03", "#52, Test Manager, round 1", "F03 counts characters."), at(3, 12))])]


def zh_line(links: Sequence[tuple]) -> str:
    """The Chinese notes line of contract E."""
    return (f"备注：{len(links)} 条（" + "、".join(f"[#{n}]({u})" for n, u in links) + "）")


def en_line(links: Sequence[tuple]) -> str:
    """The English notes line of contract E."""
    return (f"Notes from earlier work: {len(links)} ("
            + ", ".join(f"[#{n}]({u})" for n, u in links) + ")")


class ProgressCase(IssuesCase):
    """Runs ``issues`` and ``status`` on the two E cases once."""

    outs: dict = {}

    @classmethod
    def setUpClass(cls):
        """One clone per case and command."""
        if ProgressCase.outs:
            return
        cases = {"notes": e_issues_with_notes(), "others": e_issues_others_only()}
        jobs = [(name, command) for name in cases for command in ("issues", "status")]

        def run(job):
            """Runs one command on a new clone with the case's fakes."""
            name, command = job
            fakes = Fakes(**e_fakes(cases[name]))
            return Project(E_STEPS).run(command, fakes=fakes)
        ProgressCase.outs = dict(zip(jobs, parallel(run, jobs)))

    def body(self, name: str, item: str) -> str:
        """The body of the case's create or edit action for one feature."""
        report = self.issues_report(self.outs[(name, "issues")])
        found = [a for a in report["actions"]
                 if a["item"] == item and a["action"] in ("create", "edit")]
        self.assertEqual(len(found), 1, report["actions"])
        return self.body_of(found[0])


class ProgressLineTests(ProgressCase):
    """The notes line on the target's progress issue, in both parts (contract E)."""

    def assert_line(self, body: str, links: Sequence[tuple]) -> None:
        """The line once in each part, among the other lines: after the stages, before the
        dependencies."""
        chinese, english = (nonblank(part) for part in split_body(body))
        for part, line, stop, label in ((chinese, zh_line(links), "依赖：", "Chinese"),
                                        (english, en_line(links), "Depends on:", "English")):
            with self.subTest(part=label):
                self.assertEqual(part.count(line), 1, "\n".join(part))
                where = part.index(line)
                last_stage = max(i for i, text in enumerate(part)
                                 if re.match(r"^(- \[[ x]\] )?6/6 ", text))
                deps = next(i for i, text in enumerate(part) if text.startswith(stop))
                self.assertLess(last_stage, where, "\n".join(part))
                self.assertLess(where, deps, "\n".join(part))

    def test_target_issue_gets_the_line(self):
        """F02: three notes, oldest first, on #8, closed #7, and #8, one link each."""
        self.assert_line(self.body("notes", "F02"),
                         [(8, comment_url(8, 801)), (7, comment_url(7, 701)),
                          (8, comment_url(8, 803))])

    def test_a_note_on_another_features_issue(self):
        """F03's note sits on F02's #8: F03's new issue gets its line."""
        for name in ("notes", "others"):
            with self.subTest(case=name):
                self.assert_line(self.body(name, "F03"), [(8, comment_url(8, 802))])

    def test_source_issue_gets_no_line_for_another_feature(self):
        """F02's #8 holds only F03's note: F02's body has no notes line."""
        chinese, english = (nonblank(part) for part in split_body(self.body("others", "F02")))
        self.assertNotEqual(box_lines(chinese), [], "the body was rendered")
        self.assertFalse([t for t in chinese if t.startswith("备注：")], chinese)
        self.assertFalse([t for t in english if t.startswith("Notes from earlier work:")],
                         english)


class TroyCommentTests(ProgressCase):
    """A note is neither Troy's comment nor troy-mode's last one (contract E, F15 3.3)."""

    def troy_comments(self, name: str) -> list:
        """The case's ``issues.troy_comments``."""
        report = self.report_of(self.outs[(name, "status")], 0, "status")
        found = (report.get("issues") or {}).get("troy_comments")
        self.assertIsInstance(found, list, report.get("issues"))
        return found

    def test_troys_comment_before_a_note_stays(self):
        """Troy's question, then three notes: the question alone is in ``troy_comments``."""
        self.assertEqual(self.troy_comments("notes"), [
            {"issue": 8, "kind": "progress", "item": "F02", "bodies": [QUESTION]}])

    def test_a_note_alone_adds_nothing(self):
        """A note and no comment of Troy's: nothing."""
        self.assertEqual(self.troy_comments("others"), [])


if __name__ == "__main__":
    unittest.main()
