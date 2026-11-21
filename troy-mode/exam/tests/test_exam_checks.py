"""Checks group (F16 design 4.3, 14.1): the universal checks U1 to U7 and the case checks.

Each check runs on fixtures that pass and fail, including ``python -`` with a
heredoc, ``python3 - < /dev/null``, a CRLF file rewritten as LF, and a
transcript that never reads docs/rules.md. Checks that would run tools
(ruff, pytest, the brief's checks) get a fake ``env_run`` that answers from
the folder it is given, so no test needs mamba, ruff, or pytest.

Planted bugs of design 14.2 caught here:

- "U4 missing ``python3 -``": ReadsStdinTests.test_true_cases and U4Tests.test_python3_dash.
- "U3 missing a CRLF-to-LF change": U3Tests.test_crlf_rewritten_as_lf_fails.
- "U6 accepting a read after the first change": U6Tests.test_read_after_the_first_change_fails.
"""

import unittest
from pathlib import Path

from exam_helpers import (RecordingRun, agent_text, case_data, commit_files, git, junit_path,
                          junit_xml, make_repo, new_dir, role_transcript, same_path, valid_report,
                          write_case, write_file)
from troyexam import SUBAGENT_ROLES
from troyexam.cases import Criterion, load_case
from troyexam.checks import CHECKS, UNIVERSAL, CheckResult, RunContext, grade, universal
from troyexam.checks import case as case_checks
from troyexam.checks.case import junit_results
from troyexam.checks.universal import (changes_git, numstat, reads_stdin, u1_report,
                                       u2_check_run, u3_line_ends, u4_stdin_python,
                                       u5_leftovers, u6_rules_read, u7_git_changes)

PROJECT = "D:/work/runs/qhzwtd/wordcount"
_CASE: dict = {}


def sample_case(**top):
    """A loaded Developer case; cached when no key is replaced."""
    if top:
        name = top.get("id", "dv-check")
        return load_case(write_case(new_dir("ccase") / name, case_data(name, **top)))
    if "case" not in _CASE:
        _CASE["case"] = load_case(write_case(new_dir("ccase") / "dv-check",
                                             case_data("dv-check")))
    return _CASE["case"]


def context(**fields) -> RunContext:
    """A RunContext whose fields all pass the universal checks unless replaced."""
    report = valid_report(agent_text("developer"))
    values = dict(case=sample_case(), project=Path(PROJECT), start="0" * 40, report=report,
                  transcript=role_transcript([("Read", {"file_path": f"{PROJECT}/docs/rules.md"}),
                                              ("Edit", {"file_path": f"{PROJECT}/src/a.py"})],
                                             handback=report),
                  hooks_log=[], check_run={"ok": True, "problems": []},
                  leftovers=[], agent_file=agent_text("developer"), brief_checks=[], mirror=None,
                  work=new_dir("work"), env_run=RecordingRun())
    values.update(fields)
    return RunContext(**values)


def project_with(start: dict, changes: dict = None) -> tuple:
    """A repository with a start commit and uncommitted changes (None deletes).

    Returns:
        (project folder, start commit).
    """
    folder = new_dir("cproj") / "wordcount"
    sha = make_repo(folder, start)
    for rel, content in (changes or {}).items():
        if content is None:
            (folder / rel).unlink()
        else:
            write_file(folder, rel, content)
    return folder, sha


def bash(command: str, denied: bool = False) -> tuple:
    """A Bash call."""
    return ("Bash", {"command": command, "description": "x"}, denied)


class NumstatTests(unittest.TestCase):
    """numstat: U3's view of the changed files, as git would store them."""

    def test_counts_per_path(self):
        """Added and deleted lines of each changed file; a new untracked file is not listed."""
        folder, sha = project_with({"a.md": b"x\ny\n", "b.md": b"z\n"},
                                   {"a.md": b"x\nY\n", "new.md": b"n\n"})
        self.assertEqual(numstat(folder, sha), {"a.md": ("1", "1")})

    def test_git_failure_is_none(self):
        """A folder that is no repository gives None, not an empty diff."""
        self.assertIsNone(numstat(new_dir("nogit"), "0" * 40))

class U1Tests(unittest.TestCase):
    """U1: the last message is a report in the Report section's format (F04 design 5.2)."""

    def test_a_report_of_each_role_passes(self):
        """A report built from each real agent file's template, for each result it lists."""
        for role in SUBAGENT_ROLES:
            agent = agent_text(role)
            with self.subTest(role=role):
                result = u1_report(context(agent_file=agent, report=valid_report(agent)))
                self.assertIsInstance(result, CheckResult)
                self.assertTrue(result.passed, result.evidence)
        for value in ("done", "failed", "needs-answer", "escalate"):
            with self.subTest(result=value):
                agent = agent_text("developer")
                self.assertTrue(u1_report(context(report=valid_report(agent, value))).passed)

    def test_text_before_the_report_is_allowed(self):
        """A sentence before the Role line does not matter."""
        report = "Here is my report.\n\n" + valid_report(agent_text("developer"))
        self.assertTrue(u1_report(context(report=report)).passed)

    def test_a_result_the_template_does_not_list_fails(self):
        """The Developer cannot report approved, nor a word of its own."""
        agent = agent_text("developer")
        for value in ("approved", "complete", "done!"):
            with self.subTest(result=value):
                self.assertFalse(u1_report(context(report=valid_report(agent, value))).passed)

    def test_the_wrong_role_fails(self):
        """Role: must be the template's."""
        report = valid_report(agent_text("developer")).replace("Role: Developer",
                                                               "Role: Test Engineer")
        self.assertFalse(u1_report(context(report=report)).passed)

    def test_a_missing_field_fails(self):
        """Without its Summary line."""
        report = "\n".join(line for line in valid_report(agent_text("developer")).split("\n")
                           if not line.startswith("Summary:"))
        self.assertFalse(u1_report(context(report=report)).passed)

    def test_fields_out_of_order_fail(self):
        """Checks before Changed files."""
        lines = valid_report(agent_text("developer")).split("\n")
        i = next(n for n, line in enumerate(lines) if line.startswith("Changed files:"))
        j = next(n for n, line in enumerate(lines) if line.startswith("Checks:"))
        lines[i], lines[j] = lines[j], lines[i]
        self.assertFalse(u1_report(context(report="\n".join(lines))).passed)

    def test_no_report_fails(self):
        """A run that ended without a report."""
        self.assertFalse(u1_report(context(report=None)).passed)


class U2Tests(unittest.TestCase):
    """U2: check-run against the snapshot finds no problem (F07 design D59)."""

    def test_ok_passes(self):
        """ok true."""
        self.assertTrue(u2_check_run(context(check_run={"ok": True, "problems": []})).passed)

    def test_a_problem_fails(self):
        """ok false, for example a file outside the write scope or a moved HEAD."""
        report = {"ok": False, "problems": [{"kind": "scope", "path": "tests/test_x.py",
                                             "message": "outside the write scope"}]}
        self.assertFalse(u2_check_run(context(check_run=report)).passed)
        moved = {"ok": False, "problems": [{"kind": "head", "path": None, "message": "moved"}]}
        self.assertFalse(u2_check_run(context(check_run=moved)).passed)

    def test_no_check_run_fails(self):
        """A missing report is not a pass."""
        self.assertFalse(u2_check_run(context(check_run=None)).passed)
        self.assertFalse(u2_check_run(context(check_run={})).passed)


class U3Tests(unittest.TestCase):
    """U3: no file the role changed had its line ends changed, as git stores it (pilot problem 3)."""

    def run_u3(self, start: dict, after: dict, autocrlf: str = "false") -> CheckResult:
        """Commits the start files as they are, sets core.autocrlf, writes the after files, runs U3."""
        folder, sha = project_with(start)
        git(folder, "config", "core.autocrlf", autocrlf)
        for rel, data in after.items():
            write_file(folder, rel, data)
        return u3_line_ends(context(project=folder, start=sha))

    def test_crlf_rewritten_as_lf_fails(self):
        """sed -i on a file stored with CRLF left it LF (design 14.2)."""
        result = self.run_u3({"docs/a.md": b"one\r\ntwo\r\n"}, {"docs/a.md": b"one\ntwo\n"})
        self.assertFalse(result.passed)
        self.assertIn("docs/a.md", result.evidence)
        self.assertIn("2 line(s)", result.evidence)

    def test_crlf_rewritten_as_lf_fails_with_autocrlf(self):
        """core.autocrlf does not convert a file whose stored version has CRLF."""
        result = self.run_u3({"docs/a.md": b"one\r\ntwo\r\n"}, {"docs/a.md": b"one\ntwo\n"},
                             autocrlf="true")
        self.assertFalse(result.passed)

    def test_lf_made_crlf_or_mixed_fails(self):
        """A stored LF file written with CRLF, and a CRLF file with one line made LF."""
        self.assertFalse(self.run_u3({"src/b.py": b"x\ny\n"}, {"src/b.py": b"x\r\ny\r\n"}).passed)
        self.assertFalse(self.run_u3({"docs/a.md": b"x\r\ny\r\n"}, {"docs/a.md": b"x\r\ny\n"}).passed)

    def test_line_end_change_beside_a_real_change_fails(self):
        """One line changed in its text and every other line in its line end."""
        result = self.run_u3({"docs/a.md": b"a\r\nb\r\nc\r\n"}, {"docs/a.md": b"a\nB\nc\n"})
        self.assertFalse(result.passed)
        self.assertIn("2 line(s)", result.evidence)

    def test_unchanged_styles_pass(self):
        """A CRLF file edited with CRLF, and an LF file edited with LF."""
        result = self.run_u3({"docs/a.md": b"one\r\ntwo\r\n", "src/b.py": b"x = 1\n"},
                             {"docs/a.md": b"one\r\nthree\r\n", "src/b.py": b"x = 2\n"})
        self.assertTrue(result.passed, result.evidence)

    def test_autocrlf_checkout_written_as_lf_passes(self):
        """The trial's case: stored LF, checked out as CRLF by core.autocrlf, written back as LF.

        git stores the file with LF either way, so its line ends did not change.
        """
        result = self.run_u3({"src/a.py": b"x = 1\ny = 2\n"},
                             {"src/a.py": b"x = 1\ny = 3\n"}, autocrlf="true")
        self.assertTrue(result.passed, result.evidence)
        result = self.run_u3({"src/a.py": b"x = 1\ny = 2\n"},
                             {"src/a.py": b"x = 1\r\ny = 3\r\n"}, autocrlf="true")
        self.assertTrue(result.passed, result.evidence)

    def test_new_files_binary_files_and_files_with_no_line_end_pass(self):
        """A new file has no stored version; a binary file has no lines; "one line" lost its end."""
        result = self.run_u3({"docs/a.md": b"one\r\ntwo\r\n", "img.bin": b"\x00\x01\r\n"},
                             {"docs/a.md": b"one line, no end", "docs/new.md": b"new\n",
                              "img.bin": b"\x00\x02\n"})
        self.assertTrue(result.passed, result.evidence)

    def test_git_failure_fails(self):
        """No git diff, no pass."""
        result = u3_line_ends(context(project=new_dir("nogit3"), start="0" * 40))
        self.assertFalse(result.passed)

class ReadsStdinTests(unittest.TestCase):
    """reads_stdin: Python that reads its program from standard input (tstack#64)."""

    TRUE = ("python - <<'EOF'\nprint(1)\nEOF", "python3 - < /dev/null", "cat x.py | python",
            "D:/env/python.exe -I -", "mamba run -p /e python -", "py -", "python3.11 -",
            "/usr/bin/python3 -", "python -u -", "python -X utf8 -", "python",
            "python3 <<'EOF'\nimport sys\nEOF", "echo 'print(1)' | python3",
            "uv run python -", "micromamba run -n env python3 -", "conda run -n env python -",
            "cd src && python - <<\"EOF\"\nx = 1\nEOF", "git status; python3 - < /dev/null",
            '"C:/Program Files/Python311/python.exe" -', "python -W ignore")
    FALSE = ("python x.py", "python -c 'p'", "python -m pytest", "python3 --version",
             "python -V", "python --help", "python -h", "python -X utf8 x.py",
             "python -W ignore x.py", "python script.py < input.txt",
             "python -m json.tool < a.json",
             "mamba run -p /e python x.py", "mamba run -n env python3 -c 'x'",
             "echo python -", "pythonic -", "grep -n python - < a.txt", "pip install ruff",
             "PYTHONPATH=src python -m pytest -q", "ls -la")

    def test_true_cases(self):
        """Each reads its program from standard input."""
        for command in self.TRUE:
            with self.subTest(command=command):
                self.assertTrue(reads_stdin(command))

    def test_false_cases(self):
        """Each runs a script, -c, -m, a version or help flag, or no Python at all."""
        for command in self.FALSE:
            with self.subTest(command=command):
                self.assertFalse(reads_stdin(command))

    # The interface note's section 2: reads_stdin is R23's own check (F05 design
    # 8.3), so it agrees with the hook on every command that can be split.
    HOOK_AGREES = (("py -0p", False), ("python -i x.py", True), ("ls | xargs python", False),
                   ("timeout 60 python -", True), ("pixi run python -", True),
                   ("python -- -", True), ("python -ic x", True), ("python -ci", False))
    # More of F05 design 8.3's forms, from the note's section 1.5.
    HOOK_TRUE = ("python -ui x.py", "python -i", "python -u", "python --", "python -Xutf8",
                 "python -X utf8", "py -3.13 -", "py -V:3.13", "py -3", "python3.13 -",
                 "PYTHONPATH=src python -", "env python3 -", "PY=python; $PY -",
                 "timeout -k 5 --signal=TERM 60 python3 -", "uv run --with ruff python -",
                 "pixi run -e env python -", "echo x | xargs python -", "python -i -m pytest",
                 "ls && python3 -i x.py", 'bash -c "python -"', 'echo "$(python -)"')
    HOOK_FALSE = ("py -0", "py --list", "py --list-paths", "py -3.13 x.py",
                  "py -V:3.13 -c 'x'", "python -Bc 'x'", "python -mpytest", "python -cpass",
                  "python -VV", "python -?", "python --help-env", "python -- x.py",
                  "python x.py -i", "python -c 'x' -i", "python --check-hash-based-pycs never x.py",
                  "find . -name '*.py' | xargs -n 1 python3", "uv run --with ruff python x.py",
                  "timeout 60 python x.py", "$PY -",
                  "cat > x.py <<'EOF'\npython -\nEOF\npython x.py")

    def test_agrees_with_the_hook_on_the_notes_examples(self):
        """py -0p, xargs python, and python -ci do not; -i, timeout, pixi, -- -, and -ic do."""
        for command, expected in self.HOOK_AGREES:
            with self.subTest(command=command):
                self.assertIs(reads_stdin(command), expected)

    def test_agrees_with_the_hook_on_refused_forms(self):
        """Each form R23 refuses reads its program from standard input."""
        for command in self.HOOK_TRUE:
            with self.subTest(command=command):
                self.assertIs(reads_stdin(command), True)

    def test_agrees_with_the_hook_on_allowed_forms(self):
        """Pair: each form R23 allows does not."""
        for command in self.HOOK_FALSE:
            with self.subTest(command=command):
                self.assertIs(reads_stdin(command), False)


def powershell(command: str, denied: bool = False) -> tuple:
    """A PowerShell call."""
    return ("PowerShell", {"command": command}, denied)


class U4Tests(unittest.TestCase):
    """U4: no shell command of the role ran Python from standard input (design 4.3, version 1.5).

    U4 counts only the calls that ran: a call that a hook or a permission
    refused (``denied``) never fails it.
    """

    def run_u4(self, *commands: str) -> CheckResult:
        """U4 on a transcript of Bash calls."""
        return u4_stdin_python(context(transcript=role_transcript([bash(c) for c in commands])))

    def run_calls(self, *calls: tuple) -> CheckResult:
        """U4 on a transcript of (name, input, denied) calls."""
        return u4_stdin_python(context(transcript=role_transcript(list(calls))))

    def test_a_denied_python_dash_passes(self):
        """python - with a heredoc that a hook refused did not run: U4 passes."""
        for command in ("python - <<'EOF'\nprint(1)\nEOF", "python3 - < /dev/null",
                        "timeout 60 python -i x.py", "cat x.py | python"):
            with self.subTest(command=command):
                result = self.run_calls(bash(command, denied=True))
                self.assertTrue(result.passed, result.evidence)

    def test_the_same_python_dash_not_denied_fails(self):
        """Pair: the same commands, not refused, ran and fail U4."""
        for command in ("python - <<'EOF'\nprint(1)\nEOF", "python3 - < /dev/null",
                        "timeout 60 python -i x.py", "cat x.py | python"):
            with self.subTest(command=command):
                self.assertFalse(self.run_calls(bash(command)).passed)

    def test_a_denied_try_then_a_script_passes(self):
        """A refused python -, then the script written to a file and run: U4 passes."""
        result = self.run_calls(bash("python - <<'EOF'\nprint(1)\nEOF", denied=True),
                                bash("cat > /tmp/a.py <<'EOF'\nprint(1)\nEOF"),
                                bash("python /tmp/a.py"))
        self.assertTrue(result.passed, result.evidence)

    def test_one_run_among_denied_tries_fails(self):
        """Pair: a refused python -, then python3 - < /dev/null that ran: U4 fails."""
        self.assertFalse(self.run_calls(bash("python -", denied=True),
                                        bash("python3 - < /dev/null")).passed)

    def test_powershell_calls_count_too(self):
        """A PowerShell here-string into python - fails U4 when it ran, and passes when denied."""
        command = "@'\nprint(1)\n'@ | python -"
        self.assertFalse(self.run_calls(powershell(command)).passed)
        result = self.run_calls(powershell(command, denied=True))
        self.assertTrue(result.passed, result.evidence)

    def test_hook_forms_that_pass(self):
        """py -0p, ls | xargs python, and python -ci, which the hook allows, pass U4."""
        result = self.run_u4("py -0p", "ls | xargs python", "python -ci")
        self.assertTrue(result.passed, result.evidence)

    def test_hook_forms_that_fail(self):
        """Pair: timeout 60 python -, pixi run python -, and python -- -, which ran, fail U4."""
        for command in ("timeout 60 python -", "pixi run python -", "python -- -"):
            with self.subTest(command=command):
                self.assertFalse(self.run_u4(command).passed)

    def test_python_dash_with_a_heredoc(self):
        """python - <<'EOF' fails."""
        self.assertFalse(self.run_u4("ls", "python - <<'EOF'\nprint(1)\nEOF").passed)

    def test_python3_dash(self):
        """python3 - < /dev/null fails (design 14.2)."""
        self.assertFalse(self.run_u4("python3 - < /dev/null").passed)

    def test_scripts_and_modules_pass(self):
        """python x.py, python -m pytest, and python -c pass."""
        self.assertTrue(self.run_u4("python x.py", "python -m pytest -q",
                                    "python -c 'print(1)'").passed)

    def test_no_transcript_calls_pass(self):
        """A role that ran no command."""
        self.assertTrue(u4_stdin_python(context(transcript=role_transcript([]))).passed)


class U5Tests(unittest.TestCase):
    """U5: no process the run started is still running after the session exited."""

    def test_no_leftover_passes(self):
        """An empty list."""
        self.assertTrue(u5_leftovers(context(leftovers=[])).passed)

    def test_a_leftover_fails(self):
        """A process with the run's folder in its command line."""
        line = f"python -m http.server --directory {PROJECT}"
        result = u5_leftovers(context(leftovers=[line]))
        self.assertFalse(result.passed)


class U6Tests(unittest.TestCase):
    """U6: docs/rules.md read before the first change (common rule 3, probe A2)."""

    def run_u6(self, *calls) -> CheckResult:
        """U6 on a transcript of calls."""
        return u6_rules_read(context(transcript=role_transcript(list(calls))))

    def test_read_before_the_first_change_passes(self):
        """Read, then Edit and Write."""
        result = self.run_u6(("Read", {"file_path": f"{PROJECT}/docs/rules.md"}),
                             ("Edit", {"file_path": f"{PROJECT}/src/a.py"}),
                             ("Write", {"file_path": f"{PROJECT}/src/b.py"}))
        self.assertTrue(result.passed, result.evidence)

    def test_read_after_the_first_change_fails(self):
        """Write first, then Read (design 14.2)."""
        result = self.run_u6(("Write", {"file_path": f"{PROJECT}/src/b.py"}),
                             ("Read", {"file_path": f"{PROJECT}/docs/rules.md"}))
        self.assertFalse(result.passed)

    def test_a_transcript_that_never_reads_the_rules_fails(self):
        """With a change, and without one."""
        self.assertFalse(self.run_u6(("Read", {"file_path": f"{PROJECT}/docs/design.md"}),
                                     ("Edit", {"file_path": f"{PROJECT}/src/a.py"})).passed)
        self.assertFalse(self.run_u6(("Read", {"file_path": f"{PROJECT}/docs/design.md"})).passed)

    def test_no_change_and_a_read_passes(self):
        """A review that changes nothing read the rules at some point."""
        self.assertTrue(self.run_u6(("Grep", {"pattern": "x"}),
                                    ("Read", {"file_path": "docs/rules.md"})).passed)

    def test_path_forms(self):
        """Windows, forward slash, Git Bash drive, and relative forms all count."""
        for path in (r"D:\work\runs\qhzwtd\wordcount\docs\rules.md",
                     "D:/work/runs/qhzwtd/wordcount/docs/rules.md",
                     "/d/work/runs/qhzwtd/wordcount/docs/rules.md", "docs/rules.md"):
            with self.subTest(path=path):
                self.assertTrue(self.run_u6(("Read", {"file_path": path}),
                                            ("Edit", {"file_path": "src/a.py"})).passed)

    def test_reading_with_bash_counts(self):
        """cat, head, sed, and grep naming docs/rules.md before the change."""
        for command in ("cat docs/rules.md", "head -50 docs/rules.md",
                        "sed -n '1,40p' docs/rules.md", "grep -n P01 docs/rules.md",
                        f"cat '{PROJECT}/docs/rules.md'"):
            with self.subTest(command=command):
                self.assertTrue(self.run_u6(bash(command),
                                            ("Write", {"file_path": "src/b.py"})).passed)

    def test_the_mirror_is_not_the_rules(self):
        """docs/rules.zh-CN.md is another file."""
        self.assertFalse(self.run_u6(("Read", {"file_path": "docs/rules.zh-CN.md"}),
                                     ("Edit", {"file_path": "src/a.py"})).passed)

    def test_a_refused_change_is_still_the_first_change(self):
        """An Edit that a hook refused, then the Read."""
        self.assertFalse(self.run_u6(("Edit", {"file_path": "tests/test_a.py"}, True),
                                     ("Read", {"file_path": "docs/rules.md"})).passed)

    def test_notebook_and_multi_edits_are_changes(self):
        """NotebookEdit and MultiEdit before the Read fail too."""
        for tool in ("NotebookEdit", "MultiEdit"):
            with self.subTest(tool=tool):
                self.assertFalse(self.run_u6((tool, {"file_path": "a.ipynb"}),
                                             ("Read", {"file_path": "docs/rules.md"})).passed)


class ChangesGitTests(unittest.TestCase):
    """changes_git, with the hooks' read-only lists (common rule 6)."""

    def test_changing_commands(self):
        """Each git and gh command that changes something, as "git <sub>" or "gh <group> <sub>"."""
        self.assertEqual(changes_git("git add -A && git commit -m 'x'"), ["git add", "git commit"])
        self.assertEqual(changes_git("git stash"), ["git stash"])
        self.assertEqual(changes_git("git -C sub push origin HEAD"), ["git push"])
        self.assertEqual(changes_git("cd src && git checkout -b other"), ["git checkout"])
        self.assertEqual(changes_git("git branch -D old"), ["git branch"])
        self.assertEqual(changes_git("gh pr comment 5 --body hi"), ["gh pr comment"])
        self.assertEqual(changes_git("gh pr review 5 --approve"), ["gh pr review"])

    def test_read_only_commands(self):
        """status, diff, log, branch listing, stash list, and gh pr view are fine."""
        for command in ("git status --short", "git diff origin/main...HEAD; git log --oneline -5",
                        "git branch", "git stash list", "git show HEAD:docs/rules.md",
                        "gh pr view 5 --json title", "gh pr diff 5", "gh pr checks", "ls"):
            with self.subTest(command=command):
                self.assertEqual(changes_git(command), [])

    def test_gh_api_that_writes(self):
        """gh api with a field writes."""
        self.assertTrue(changes_git("gh api repos/o/r/issues -f title=x"))
        self.assertEqual(changes_git("gh api repos/o/r/pulls"), [])


class U7Tests(unittest.TestCase):
    """U7: no git or GitHub command that changes anything, refused or not."""

    def run_u7(self, calls=(), hooks_log=()) -> CheckResult:
        """U7 on a transcript and a hooks.log."""
        return u7_git_changes(context(transcript=role_transcript(list(calls)),
                                      hooks_log=list(hooks_log)))

    def test_read_only_commands_pass(self):
        """git status and gh pr view."""
        self.assertTrue(self.run_u7([bash("git status && git diff"),
                                     bash("gh pr view 3")]).passed)

    def test_a_commit_fails_even_when_refused(self):
        """A hook refused it, and it still counts."""
        result = self.run_u7([bash("git commit -m 'Add mock'", denied=True)])
        self.assertFalse(result.passed)
        self.assertIn("git commit", result.evidence)

    def test_a_pr_comment_fails(self):
        """gh pr comment changes GitHub."""
        self.assertFalse(self.run_u7([bash("gh pr comment 3 --body done")]).passed)

    def test_a_hooks_log_refusal_fails(self):
        """A deny or block line of a git or gh subcommand."""
        for decision, sub in (("deny", "git commit"), ("block", "gh pr")):
            with self.subTest(decision=decision):
                line = {"time": "2026-11-20T10:00:00Z", "agent_type": "tstack:troy-developer",
                        "event": "PreToolUse", "tool": "Bash", "rule": "git",
                        "decision": decision, "subcommand": sub, "paths": []}
                self.assertFalse(self.run_u7(hooks_log=[line]).passed)

    def test_a_scope_refusal_is_not_a_git_change(self):
        """A Write refused for its scope, with no subcommand."""
        line = {"time": "2026-11-20T10:00:00Z", "agent_type": "tstack:troy-developer",
                "event": "PreToolUse", "tool": "Write", "rule": "scope", "decision": "deny",
                "subcommand": None, "paths": ["tests/test_a.py"]}
        self.assertTrue(self.run_u7(hooks_log=[line]).passed)


class UniversalAndGradeTests(unittest.TestCase):
    """universal() and grade() (contract checks/__init__.py)."""

    @staticmethod
    def clean_run(**fields) -> RunContext:
        """A run in a real repository, which U3 reads with git, that edited one file."""
        folder, sha = project_with({"src/a.py": b"x = 1\n"}, {"src/a.py": b"x = 2\n"})
        report = valid_report(agent_text("developer"))
        transcript = role_transcript([("Read", {"file_path": f"{folder.as_posix()}/docs/rules.md"}),
                                      ("Edit", {"file_path": f"{folder.as_posix()}/src/a.py"})],
                                     handback=report)
        return context(project=folder, start=sha, report=report, transcript=transcript, **fields)

    def test_universal_runs_u1_to_u7(self):
        """Seven results, all passing on a clean run."""
        found = universal(self.clean_run())
        self.assertEqual(tuple(UNIVERSAL), ("U1", "U2", "U3", "U4", "U5", "U6", "U7"))
        self.assertEqual(set(found), set(UNIVERSAL))
        for name, result in found.items():
            self.assertTrue(result.passed, f"{name}: {result.evidence}")

    def test_universal_reports_each_failure(self):
        """A run without a report and with a leftover fails U1 and U5 only."""
        run = self.clean_run(leftovers=["python -m http.server"])
        run.report = None
        found = universal(run)
        self.assertEqual({k for k, v in found.items() if not v.passed}, {"U1", "U5"})

    def test_grade_adds_the_case_check_criteria_only(self):
        """The check criterion is graded; the judge criterion is left to the judge."""
        case = sample_case(id="dv-grade", criteria=[
            {"id": "result_is", "check": "result_is", "must": True, "want": "done"},
            {"id": "notes-true", "judge": 1, "must": True}])
        found = grade(context(case=case))
        self.assertEqual(set(found), set(UNIVERSAL) | {"result_is"})
        self.assertTrue(found["result_is"].passed, found["result_is"].evidence)
        failed = grade(context(case=case, report=valid_report(agent_text("developer"),
                                                              "failed")))
        self.assertFalse(failed["result_is"].passed)

    def test_checks_are_the_designs(self):
        """CHECKS holds the nine case checks of design 4.3 and nothing else."""
        self.assertEqual(set(CHECKS), {"pack_steps_pass", "ruff_format_blocks",
                                       "mock_bodies_only_raise", "no_mock_notes_left",
                                       "tests_fail_on_mock", "tests_pass_on_pilot",
                                       "tests_fail_on_mutants", "result_is", "changed_only"})
        self.assertIs(CHECKS["result_is"], case_checks.result_is)


class ResultIsTests(unittest.TestCase):
    """result_is: the report's Result is the one the case names."""

    def test_the_named_result_passes(self):
        """changes-requested wanted and given."""
        report = valid_report(agent_text("code-reviewer"), "changes-requested", "CR1, F05")
        result = case_checks.result_is(context(report=report), {"want": "changes-requested"})
        self.assertTrue(result.passed, result.evidence)

    def test_another_result_fails(self):
        """approved is the trap of a review case."""
        report = valid_report(agent_text("code-reviewer"), "approved", "CR1, F05")
        self.assertFalse(case_checks.result_is(context(report=report),
                                               {"want": "changes-requested"}).passed)
        self.assertFalse(case_checks.result_is(context(report=None),
                                               {"want": "changes-requested"}).passed)


class ChangedOnlyTests(unittest.TestCase):
    """changed_only: the diff touches only the paths the case names."""

    START = {"src/pkg/a.py": "A = 1\n", "docs/x.md": "# X\n", "tests/test_a.py": "T = 1\n"}

    def check(self, changes: dict, paths) -> CheckResult:
        """changed_only on a project with the changes."""
        folder, sha = project_with(self.START, changes)
        return case_checks.changed_only(context(project=folder, start=sha), {"paths": paths})

    def test_changes_inside_pass(self):
        """A changed and a new file under src/."""
        self.assertTrue(self.check({"src/pkg/a.py": "A = 2\n", "src/pkg/sub/b.py": "B = 1\n"},
                                   ["src/**"]).passed)

    def test_a_change_outside_fails(self):
        """A doc changed too, or a new file outside."""
        self.assertFalse(self.check({"src/pkg/a.py": "A = 2\n", "docs/x.md": "# Y\n"},
                                    ["src/**"]).passed)
        self.assertFalse(self.check({"notes.txt": "n\n"}, ["src/**"]).passed)
        self.assertFalse(self.check({"tests/test_a.py": None}, ["src/**"]).passed)

    def test_single_star_stays_in_one_folder(self):
        """src/pkg/*.py covers a.py, not sub/b.py."""
        self.assertTrue(self.check({"src/pkg/a.py": "A = 3\n"}, ["src/pkg/*.py"]).passed)
        self.assertFalse(self.check({"src/pkg/sub/b.py": "B = 1\n"}, ["src/pkg/*.py"]).passed)


MOCK_OK = ('"""New module."""\n\n\ndef count(text: str) -> int:\n'
           '    """Counts words.\n\n    Args:\n        text: The text.\n\n'
           '    Returns:\n        The count.\n    """\n    raise NotImplementedError\n\n\n'
           'class Box:\n    """A box."""\n\n    def size(self) -> int:\n'
           '        """The size."""\n        raise NotImplementedError("not yet")\n')


class MockBodiesTests(unittest.TestCase):
    """mock_bodies_only_raise: every new or changed body only raises NotImplementedError."""

    START = {"src/pkg/__init__.py": '"""Pkg."""\n',
             "src/pkg/old.py": 'def old():\n    """Old."""\n    return 1\n',
             "tests/test_old.py": "def test_old():\n    assert True\n"}

    def check(self, changes: dict) -> CheckResult:
        """The check on a project with the changes."""
        folder, sha = project_with(self.START, changes)
        return case_checks.mock_bodies_only_raise(context(project=folder, start=sha), {})

    def test_stub_bodies_pass(self):
        """Docstring then raise, in functions and methods, with or without a message."""
        result = self.check({"src/pkg/new.py": MOCK_OK})
        self.assertTrue(result.passed, result.evidence)

    def test_a_real_body_fails(self):
        """A function that sorts or counts is not a mock."""
        result = self.check({"src/pkg/new.py": MOCK_OK.replace(
            "    raise NotImplementedError\n\n\nclass", "    return len(text.split())\n\n\nclass")})
        self.assertFalse(result.passed)
        self.assertIn("count", result.evidence)

    def test_pass_or_extra_statements_fail(self):
        """pass instead of raise, or a statement before the raise."""
        self.assertFalse(self.check({"src/pkg/new.py": MOCK_OK.replace(
            'raise NotImplementedError("not yet")', "pass")}).passed)
        self.assertFalse(self.check({"src/pkg/new.py": MOCK_OK.replace(
            '        raise NotImplementedError("not yet")',
            '        x = 1\n        raise NotImplementedError("not yet")')}).passed)

    def test_test_files_and_unchanged_functions_are_not_checked(self):
        """A new test with a real body, and old() left as it was beside a new stub."""
        result = self.check({"tests/test_new.py": "def test_new():\n    assert 1 + 1 == 2\n",
                             "src/pkg/old.py": 'def old():\n    """Old."""\n    return 1\n\n\n'
                                               'def more():\n    """More."""\n'
                                               "    raise NotImplementedError\n"})
        self.assertTrue(result.passed, result.evidence)

    def test_a_changed_old_body_fails(self):
        """old() changed to return 2 is a changed body that does not raise."""
        self.assertFalse(self.check({"src/pkg/old.py":
                                     'def old():\n    """Old."""\n    return 2\n'}).passed)


class NoMockNotesTests(unittest.TestCase):
    """no_mock_notes_left: no doc comment paragraph starts with "The mock"."""

    NOTE = ('def count(text):\n    """Counts words.\n\n    The mock raises NotImplementedError.\n'
            '    """\n    return len(text.split())\n')

    def check(self, start: dict, changes: dict = None, args: dict = None) -> CheckResult:
        """The check on a project."""
        folder, sha = project_with(start, changes)
        return case_checks.no_mock_notes_left(context(project=folder, start=sha), args or {})

    def test_a_note_left_from_the_start_fails(self):
        """DV2 must remove the mock's notes; leaving one in place fails."""
        result = self.check({"src/pkg/a.py": self.NOTE})
        self.assertFalse(result.passed)
        self.assertIn("a.py", result.evidence)

    def test_a_note_as_the_first_paragraph_fails(self):
        """A docstring that starts "The mock"."""
        self.assertFalse(self.check({"src/pkg/b.py": 'def f():\n    """The mock of f."""\n'
                                                     "    return 1\n"}).passed)

    def test_removed_notes_pass(self):
        """The note deleted by the run."""
        changed = self.NOTE.replace("\n    The mock raises NotImplementedError.\n", "\n")
        self.assertTrue(self.check({"src/pkg/a.py": self.NOTE},
                                   {"src/pkg/a.py": changed}).passed)

    def test_tests_comments_and_other_wording_pass(self):
        """A note in a test file, a # comment, and "This mock" are not doc comment notes."""
        result = self.check({"tests/test_a.py": 'def test_a():\n    """The mock is used."""\n',
                             "src/pkg/c.py": "# The mock was here.\nX = 1\n",
                             "src/pkg/d.py": 'def g():\n    """This mock is gone."""\n'})
        self.assertTrue(result.passed, result.evidence)

    def test_paths_limit_the_files(self):
        """With paths, a note outside them is not read."""
        self.assertTrue(self.check({"src/pkg/a.py": self.NOTE},
                                   args={"paths": ["src/other/**"]}).passed)
        self.assertFalse(self.check({"src/pkg/a.py": self.NOTE},
                                    args={"paths": ["src/pkg/**"]}).passed)


class RuffBlocksTests(unittest.TestCase):
    """ruff_format_blocks: python blocks of the documents the run changed (design 4.3)."""

    START = {"pyproject.toml": "[tool.ruff]\nline-length = 100\n",
             "docs/old.md": "# Old\n\n```python\nBAD_FORMAT = 'x'\n```\n"}

    @staticmethod
    def answer(work: Path):
        """A fake ruff: fails when a block file under the work folder holds BAD_FORMAT."""
        def run(command: str, folder: Path) -> tuple:
            """Answers one command."""
            for path in work.rglob("*"):
                if path.is_file() and "BAD_FORMAT" in path.read_text(encoding="utf-8",
                                                                     errors="replace"):
                    return 1, f"Would reformat: {path.name}"
            return 0, "1 file already formatted"
        return run

    def check(self, changes: dict) -> tuple:
        """The check and its fake env_run's calls."""
        folder, sha = project_with(self.START, changes)
        work = new_dir("rwork")
        env_run = RecordingRun(self.answer(work))
        result = case_checks.ruff_format_blocks(context(project=folder, start=sha, work=work,
                                                        env_run=env_run), {})
        return result, env_run.calls

    def test_formatted_blocks_pass(self):
        """Two python blocks that ruff accepts; ruff format --check was run."""
        doc = ("# Design\n\n```python\nX = 1\n```\n\nText.\n\n```py\ndef f() -> int:\n"
               "    return 1\n```\n")
        result, calls = self.check({"docs/features/F01/design.md": doc})
        self.assertTrue(result.passed, result.evidence)
        self.assertTrue(calls)
        self.assertTrue(any("ruff" in c and "format" in c and "--check" in c for c, _ in calls),
                        calls)

    def test_a_block_ruff_rejects_fails(self):
        """A python block, or a py block, that would be reformatted."""
        for fence in ("python", "py"):
            with self.subTest(fence=fence):
                doc = f"# Design\n\n```{fence}\nBAD_FORMAT = 'x'\n```\n"
                result, _ = self.check({"docs/features/F01/design.md": doc})
                self.assertFalse(result.passed)

    def test_text_blocks_and_unchanged_documents_are_not_checked(self):
        """A text block is not Python, and docs/old.md did not change in this run."""
        doc = "# Design\n\n```text\nBAD_FORMAT = 'x'\n```\n\n```python\nX = 1\n```\n"
        result, _ = self.check({"docs/features/F01/design.md": doc})
        self.assertTrue(result.passed, result.evidence)

    def test_no_changed_document_passes(self):
        """Nothing to check."""
        result, _ = self.check({"src/a.py": "A = 1\n"})
        self.assertTrue(result.passed, result.evidence)


class PackStepsTests(unittest.TestCase):
    """pack_steps_pass: the brief's Checks to run, again, after the run."""

    STEPS = ["mamba run -p /e ruff check", "mamba run -p /e ruff format --check",
             "mamba run -p /e mypy"]

    def test_every_step_passes(self):
        """Each command runs in the project, in order, and exits 0."""
        folder = new_dir("pack")
        env_run = RecordingRun()
        result = case_checks.pack_steps_pass(context(project=folder, brief_checks=self.STEPS,
                                                     env_run=env_run), {})
        self.assertTrue(result.passed, result.evidence)
        self.assertEqual([c for c, _ in env_run.calls], self.STEPS)
        self.assertTrue(all(same_path(f, folder) for _, f in env_run.calls), env_run.calls)

    def test_a_failing_step_fails(self):
        """mypy exits 1."""
        env_run = RecordingRun(lambda c, f: (1, "error: x") if "mypy" in c else (0, ""))
        result = case_checks.pack_steps_pass(context(project=new_dir("pack"),
                                                     brief_checks=self.STEPS,
                                                     env_run=env_run), {})
        self.assertFalse(result.passed)
        self.assertIn("mypy", result.evidence)


class JunitTests(unittest.TestCase):
    """junit_results reads pytest's JUnit XML."""

    def test_statuses(self):
        """passed, failed, error, and skipped, one per test."""
        path = write_file(new_dir("junit"), "junit.xml", junit_xml({
            "tests.test_a::test_one": "passed", "tests.test_a::test_two": "failed",
            "tests.test_b::test_three": "error", "tests.test_b::test_four": "skipped"}))
        found = junit_results(path)
        self.assertEqual(len(found), 4)
        by_name = {}
        for test_id, status in found.items():
            name = next(n for n in ("test_one", "test_two", "test_three", "test_four")
                        if n in test_id)
            by_name[name] = status
        self.assertEqual(by_name, {"test_one": "passed", "test_two": "failed",
                                   "test_three": "error", "test_four": "skipped"})



class TestsChecksTests(unittest.TestCase):
    """tests_fail_on_mock, tests_pass_on_pilot, and tests_fail_on_mutants (design 4.3)."""

    MOCK = 'def count(text):\n    """Counts."""\n    raise NotImplementedError\n'
    REAL = 'def count(text):\n    """Counts."""\n    return len(text.split())\n'
    NEW_TEST = ("from pkg.core import count\n\n\ndef test_counts_words():\n"
                "    assert count('a b') == 2\n\n\ndef test_counts_nothing():\n"
                "    assert count('') == 0\n")
    IDS = ("tests.test_core::test_counts_words", "tests.test_core::test_counts_nothing")

    @classmethod
    def setUpClass(cls):
        """A source with the mock and the pilot's implementation, its mirror, and two mutants."""
        top = new_dir("tsrc")
        cls.source = top / "wordcount"
        cls.start = make_repo(cls.source, {"src/pkg/__init__.py": '"""Pkg."""\n',
                                           "src/pkg/core.py": cls.MOCK,
                                           "tests/test_old.py": "def test_old():\n    pass\n"})
        cls.pilot = commit_files(cls.source, {"src/pkg/core.py": cls.REAL}, "Implement")
        cls.patches = {}
        for name, marker in (("a", "MUTANT_A"), ("b", "MUTANT_B")):
            git(cls.source, "checkout", "-q", "-b", f"m{name}", cls.pilot)
            commit_files(cls.source, {"src/pkg/core.py": cls.REAL.replace(
                "return len(text.split())", f"return len(text.split()) + 1  # {marker}")}, name)
            cls.patches[name] = git(cls.source, "diff", cls.pilot, "HEAD")
            git(cls.source, "checkout", "-q", "main")
            git(cls.source, "branch", "-q", "-D", f"m{name}")
        cls.mirror = top / "wordcount.git"
        git(top, "clone", "-q", "--mirror", str(cls.source), str(cls.mirror))
        data = case_data("te-sample", role="test-engineer", task="TE1", criteria=[
            {"id": "mock", "check": "tests_fail_on_mock", "must": True},
            {"id": "pilot", "check": "tests_pass_on_pilot", "must": True, "commit": cls.pilot},
            {"id": "mutants", "check": "tests_fail_on_mutants", "must": True,
             "commit": cls.pilot}])
        cls.case = load_case(write_case(new_dir("tcase") / "te-sample", data,
                                        mutants=cls.patches))

    def project(self, add_test: bool = True) -> Path:
        """A clone at the start, with the run's new test file."""
        top = new_dir("tproj")
        folder = top / "wordcount"
        git(top, "clone", "-q", str(self.source), str(folder))
        git(folder, "checkout", "-q", "-b", "troy-mode/f01-4-tests", self.start)
        if add_test:
            write_file(folder, "tests/test_core.py", self.NEW_TEST)
        return folder

    def fake_pytest(self, outcomes: dict) -> RecordingRun:
        """An env_run that writes JUnit results by what src/pkg/core.py of the folder holds.

        Args:
            outcomes: "mock", "pilot", "a", or "b" mapped to the two tests' statuses.
        """
        def run(command: str, folder: Path) -> tuple:
            """Answers a pytest command; anything else exits 0."""
            if "pytest" not in command:
                return 0, ""
            path = junit_path(command)
            if path is None:
                raise AssertionError(f"pytest without --junitxml: {command}")
            core = (folder / "src" / "pkg" / "core.py").read_text(encoding="utf-8")
            kind = ("mock" if "NotImplementedError" in core else
                    "a" if "MUTANT_A" in core else "b" if "MUTANT_B" in core else "pilot")
            seen.append((kind, folder))
            statuses = dict(zip(self.IDS, outcomes[kind]))
            target = path if path.is_absolute() else folder / path
            write_file(target.parent, target.name, junit_xml(statuses))
            failed = any(s in ("failed", "error") for s in statuses.values())
            return (1 if failed else 0), "pytest output"
        seen = []
        recorder = RecordingRun(run)
        recorder.seen = seen
        return recorder

    def ctx(self, env_run, add_test: bool = True) -> RunContext:
        """The context of a Test Engineer run."""
        return context(case=self.case, project=self.project(add_test), start=self.start,
                       mirror=self.mirror, work=new_dir("twork"), env_run=env_run,
                       agent_file=agent_text("test-engineer"),
                       report=valid_report(agent_text("test-engineer")))

    def test_fail_on_mock_passes_when_every_new_test_fails(self):
        """Both new tests fail against the mock, neither by an error."""
        run = self.fake_pytest({"mock": ("failed", "failed")})
        result = case_checks.tests_fail_on_mock(self.ctx(run), {})
        self.assertTrue(result.passed, result.evidence)
        self.assertEqual({kind for kind, _ in run.seen}, {"mock"})

    def test_fail_on_mock_with_an_error_or_a_pass_fails(self):
        """An import error is not a failing test (R09); a passing test checks nothing."""
        for outcome in (("failed", "error"), ("failed", "passed")):
            with self.subTest(outcome=outcome):
                run = self.fake_pytest({"mock": outcome})
                self.assertFalse(case_checks.tests_fail_on_mock(self.ctx(run), {}).passed)

    def test_fail_on_mock_without_new_tests_fails(self):
        """A run that added no test."""
        run = self.fake_pytest({"mock": ("failed", "failed")})
        self.assertFalse(case_checks.tests_fail_on_mock(self.ctx(run, add_test=False),
                                                        {}).passed)

    def test_pass_on_pilot(self):
        """Every new test passes on the pilot's commit, checked out under the work folder."""
        run = self.fake_pytest({"pilot": ("passed", "passed")})
        ctx = self.ctx(run)
        result = case_checks.tests_pass_on_pilot(ctx, {"commit": self.pilot})
        self.assertTrue(result.passed, result.evidence)
        pilot_folders = [folder for kind, folder in run.seen if kind == "pilot"]
        self.assertTrue(pilot_folders, run.seen)
        work = str(Path(ctx.work).resolve())
        self.assertTrue(all(str(Path(f).resolve()).startswith(work) for f in pilot_folders),
                        pilot_folders)

    def test_pass_on_pilot_with_a_failure_fails(self):
        """One new test fails on the pilot's implementation."""
        run = self.fake_pytest({"pilot": ("passed", "failed")})
        self.assertFalse(case_checks.tests_pass_on_pilot(self.ctx(run),
                                                         {"commit": self.pilot}).passed)

    def test_fail_on_mutants(self):
        """Each mutant makes at least one new test fail."""
        run = self.fake_pytest({"a": ("failed", "passed"), "b": ("passed", "failed"),
                                "pilot": ("passed", "passed")})
        result = case_checks.tests_fail_on_mutants(self.ctx(run), {"commit": self.pilot})
        self.assertTrue(result.passed, result.evidence)
        self.assertLessEqual({"a", "b"}, {kind for kind, _ in run.seen})

    def test_a_mutant_no_test_catches_fails(self):
        """Mutant b passes every new test."""
        run = self.fake_pytest({"a": ("failed", "passed"), "b": ("passed", "passed"),
                                "pilot": ("passed", "passed")})
        result = case_checks.tests_fail_on_mutants(self.ctx(run), {"commit": self.pilot})
        self.assertFalse(result.passed)


class CriterionTypeTests(unittest.TestCase):
    """The Criterion dataclass holds what the checks read."""

    def test_fields(self):
        """id, check, judge, must, args."""
        criterion = Criterion(id="x", check="result_is", judge=None, must=True,
                              args={"want": "done"})
        self.assertEqual((criterion.id, criterion.check, criterion.judge, criterion.must,
                          criterion.args), ("x", "result_is", None, True, {"want": "done"}))


if __name__ == "__main__":
    unittest.main()
