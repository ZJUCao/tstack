"""Projects group (F16 design 4.2, 11.1, 14.1): the work root and one run's project.

A project built from a small local start repository holds no commit after
the start, in the project or in its origin; origin has HEAD on main;
start.patch applies and is committed with the PR's title; core.hooksPath and
core.autocrlf are set; the gh stand-in answers pr view, pr diff, and pr
checks and refuses pr comment, api, and every other command.

Planted bugs of design 14.2 caught here:

- "a later commit reachable in the case's origin":
  BuildProjectTests.test_no_later_commit_in_origin (and ..._in_project).
- "the gh stand-in letting gh pr comment through":
  GhStubTests.test_pr_comment_is_refused_and_changes_nothing.
"""

import json
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path

from exam_helpers import (START_NAME, case_data, commit_files, git, git_proc, lf_text, make_repo,
                          new_dir, object_exists, rev_list_all, same_path, word_hits, write_case,
                          write_file)
from troyexam import (AGENT_PREFIX, CLI_VARIABLE, DEFAULT_ROOT, INSTALLED_OFF, PLUGIN_NAME,
                      ROOT_VARIABLE, SUBAGENT_ROLES)
from troyexam.cases import load_case
from troyexam.errors import ExamError
from troyexam.ghstub import OFFLINE, write_gh
from troyexam.paths import Layout, work_root
from troyexam.project import (RunFolder, build_project, copy_plugin, ensure_mirror,
                              new_run_folder, source_url)

HOOK = ".troy-mode/checks/git-hooks/pre-commit"
TITLE = "[F01 3/6 mock] Count words"
BRANCH = "troy-mode/f01-3-mock"


def start_repository(folder: Path) -> dict:
    """A start repository named wordcount: first, start, and later commits.

    The first commit holds a pre-commit hook that always fails, at the path
    core.hooksPath names, so a project that runs its hooks cannot commit.

    Returns:
        "path", "first", "start", "later", and "patch" (a diff of a round-1
        head on the start commit, made on a branch that is then deleted).
    """
    path = folder / START_NAME
    first = make_repo(path, {
        "README.md": "# wordcount\n\nCounts words.\n",
        "docs/rules.md": "# Rules\n\n| ID | Rule |\n| --- | --- |\n| R01 | One commit. |\n",
        ".troy-mode/config.toml": "[lang]\nname = \"python\"\n",
        HOOK: "#!/bin/sh\necho refused by the project hook >&2\nexit 1\n",
        "src/wordcount/__init__.py": '"""Counts words."""\n',
    }, "[rules] Set up troy-mode", executable=[HOOK])
    start = commit_files(path, {"docs/notes.md": "# Notes\n\nFirst.\n",
                                "src/wordcount/core.py": "def count(text):\n    return 0\n"},
                         "[F01 2/6 test-plan] Count words")
    git(path, "checkout", "-q", "-b", "side")
    commit_files(path, {"docs/notes.md": "# Notes\n\nFirst.\nSecond.\n",
                        "docs/review.md": "# Review\n\nRound one.\n"}, "side")
    patch = git(path, "diff", start, "side")
    git(path, "checkout", "-q", "main")
    git(path, "branch", "-q", "-D", "side")
    later = commit_files(path, {"src/wordcount/later.py": "LATER = 1\n"},
                         "[F01 3/6 mock] Count words")
    return {"path": path, "first": first, "start": start, "later": later, "patch": patch}


class ConstantsTests(unittest.TestCase):
    """troyexam's constants after F19 (contract, design 6.1 and 11.3)."""

    def test_names(self):
        """The plugin copy is tstack, roles are tstack:troy-<role>, the installed one is off."""
        self.assertEqual(PLUGIN_NAME, "tstack")
        self.assertEqual(AGENT_PREFIX, "tstack:troy-")
        self.assertEqual(INSTALLED_OFF, '{"enabledPlugins":{"tstack@tstack":false}}')
        self.assertEqual(json.loads(INSTALLED_OFF), {"enabledPlugins": {"tstack@tstack": False}})

    def test_roles_and_variables(self):
        """The six subagent roles (design 3) and the two variables (11.1, 11.3)."""
        self.assertEqual(tuple(SUBAGENT_ROLES), ("architect", "interface-designer",
                                                 "test-manager", "developer", "test-engineer",
                                                 "code-reviewer"))
        self.assertEqual((ROOT_VARIABLE, CLI_VARIABLE), ("TROY_EXAM_ROOT", "TROY_EXAM_CLI"))
        self.assertEqual(DEFAULT_ROOT, r"D:\Troy\troy-mode-work")


class LayoutTests(unittest.TestCase):
    """The work root and its folders (design 11.1)."""

    def test_work_root_default_and_variable(self):
        """D:\\Troy\\troy-mode-work unless TROY_EXAM_ROOT names another folder."""
        self.assertEqual(work_root({}), Path(r"D:\Troy\troy-mode-work"))
        self.assertEqual(work_root({"TROY_EXAM_ROOT": "/tmp/other-root"}), Path("/tmp/other-root"))

    def test_layout_folders(self):
        """mirrors, envs, runs, results, cases, and climb under the root."""
        root = Path("/work/root")
        layout = Layout(root)
        self.assertEqual(layout.root, root)
        for name in ("mirrors", "envs", "runs", "results", "cases", "climb"):
            with self.subTest(folder=name):
                self.assertEqual(getattr(layout, name), root / name)

    def test_layout_paths(self):
        """A mirror, a case log, an exam's results, and a climb log."""
        root = Path("/work/root")
        layout = Layout(root)
        self.assertEqual(layout.mirror("ZJUCao/recipe-menu"), root / "mirrors" / "recipe-menu.git")
        self.assertEqual(layout.case_log("dv-mock-notes"), root / "cases" / "dv-mock-notes.tsv")
        self.assertEqual(layout.result("2026-11-20-1"), root / "results" / "2026-11-20-1")
        self.assertEqual(layout.climb_log("notes"), root / "climb" / "notes" / "decision.tsv")


class SourceUrlTests(unittest.TestCase):
    """Where a mirror is cloned from (contract project.py)."""

    def test_a_local_folder_is_used_as_is(self):
        """Tests start from local folders."""
        folder = new_dir("local")
        self.assertEqual(source_url(str(folder)), str(folder))

    def test_a_github_name_becomes_its_url(self):
        """owner/name becomes https://github.com/owner/name.git."""
        self.assertEqual(source_url("ZJUCao/recipe-menu"),
                         "https://github.com/ZJUCao/recipe-menu.git")


class MirrorTests(unittest.TestCase):
    """ensure_mirror clones, fetches, and refuses an unknown commit (design 4.2 step 1)."""

    @classmethod
    def setUpClass(cls):
        """One start repository and one work root."""
        cls.repo = start_repository(new_dir("mirsrc"))
        cls.layout = Layout(new_dir("mirroot"))
        cls.name = cls.repo["path"].as_posix()
        cls.mirror = ensure_mirror(cls.layout, cls.name, cls.repo["start"])

    def test_the_mirror_is_a_bare_clone_at_its_layout_path(self):
        """mirrors/wordcount.git, bare, holding the start commit."""
        self.assertTrue(same_path(self.mirror, self.layout.mirror(self.name)))
        self.assertEqual(Path(self.mirror).name, "wordcount.git")
        self.assertEqual(git(self.mirror, "rev-parse", "--is-bare-repository").strip(), "true")
        self.assertTrue(object_exists(Path(self.mirror), self.repo["start"], bare=True))

    def test_a_newer_commit_is_fetched(self):
        """A commit made after the mirror was cloned is fetched when a case needs it."""
        newer = commit_files(self.repo["path"], {"docs/newer.md": "# Newer\n"}, "Newer")
        self.assertFalse(object_exists(Path(self.mirror), newer, bare=True))
        again = ensure_mirror(self.layout, self.name, newer)
        self.assertTrue(same_path(again, self.mirror))
        self.assertTrue(object_exists(Path(self.mirror), newer, bare=True))

    def test_an_unknown_commit_raises(self):
        """A commit the source does not have: ExamError."""
        with self.assertRaises(ExamError):
            ensure_mirror(self.layout, self.name, "1" * 40)


class RunFolderTests(unittest.TestCase):
    """new_run_folder (design 4.2 step 7, contract)."""

    def test_folder_names(self):
        """runs/<six letters>/ holding wordcount, wordcount.git, tstack, and bin."""
        layout = Layout(new_dir("rfroot"))
        folder = new_run_folder(layout, "ZJUCao/wordcount", random.Random(7))
        self.assertIsInstance(folder, RunFolder)
        self.assertTrue(same_path(folder.root.parent, layout.runs))
        self.assertRegex(folder.root.name, r"^[a-z]{6}$")
        self.assertEqual(word_hits(folder.root.name), [])
        self.assertTrue(folder.root.is_dir())
        self.assertEqual(folder.project, folder.root / "wordcount")
        self.assertEqual(folder.origin, folder.root / "wordcount.git")
        self.assertEqual(folder.plugin, folder.root / "tstack")
        self.assertEqual(folder.bin, folder.root / "bin")

    def test_a_used_name_is_not_used_again(self):
        """The same random sequence twice still gives two folders."""
        layout = Layout(new_dir("rfroot"))
        first = new_run_folder(layout, "ZJUCao/wordcount", random.Random(11))
        second = new_run_folder(layout, "ZJUCao/wordcount", random.Random(11))
        self.assertNotEqual(first.root, second.root)
        self.assertTrue(first.root.is_dir() and second.root.is_dir())


class BuildProjectTests(unittest.TestCase):
    """build_project: steps 1, 2, 3, and 5 of design 4.2, for a first round and a review."""

    @classmethod
    def setUpClass(cls):
        """Builds one first-round project and one review project from one start repository."""
        cls.repo = start_repository(new_dir("bpsrc"))
        cls.layout = Layout(new_dir("bproot"))
        name = cls.repo["path"].as_posix()
        start = {"repository": name, "commit": cls.repo["start"], "branch": BRANCH,
                 "pilot": ["#3"]}
        cases = new_dir("bpcases")
        cls.plain_case = load_case(write_case(cases / "dv-plain", case_data(
            "dv-plain", item="F01", start=start)))
        cls.review_case = load_case(write_case(cases / "cr-review", case_data(
            "cr-review", role="code-reviewer", task="CR1", item="F01",
            start=dict(start, title=TITLE), criteria=[
                {"id": "result", "check": "result_is", "must": True,
                 "want": "changes-requested"}]), start_patch=cls.repo["patch"]))
        cls.mirror = ensure_mirror(cls.layout, name, cls.repo["start"])
        cls.plain = new_run_folder(cls.layout, name, random.Random(1))
        cls.plain_head = build_project(cls.plain_case, cls.plain, cls.mirror)
        cls.review = new_run_folder(cls.layout, name, random.Random(2))
        cls.review_head = build_project(cls.review_case, cls.review, cls.mirror)

    def test_history_ends_at_the_start(self):
        """Every commit of the project is the start commit or one of its ancestors."""
        expected = set(git(self.repo["path"], "rev-list", self.repo["start"]).split())
        self.assertEqual(rev_list_all(self.plain.project), expected)
        self.assertEqual(set(git(self.plain.origin.parent, "--git-dir", str(self.plain.origin),
                                 "rev-list", "--all").split()), expected)

    def test_no_later_commit_in_project(self):
        """The later commit cannot be read in the project, reachable or not (4.2 step 1)."""
        self.assertFalse(object_exists(self.plain.project, self.repo["later"]))
        self.assertFalse(object_exists(self.review.project, self.repo["later"]))

    def test_no_later_commit_in_origin(self):
        """Nor in its local origin (design 14.2: a later commit reachable in the origin)."""
        for folder in (self.plain, self.review):
            with self.subTest(origin=folder.origin.name):
                self.assertFalse(object_exists(folder.origin, self.repo["later"], bare=True))
                self.assertNotIn(self.repo["later"], rev_list_all(folder.origin, bare=True))

    def test_branch_and_head_of_a_first_round(self):
        """The case's branch, made from the start commit and checked out; main at the start."""
        project = self.plain.project
        self.assertEqual(git(project, "symbolic-ref", "--short", "HEAD").strip(), BRANCH)
        self.assertEqual(git(project, "rev-parse", "HEAD").strip(), self.repo["start"])
        self.assertEqual(git(project, "rev-parse", "main").strip(), self.repo["start"])
        self.assertEqual(self.plain_head, self.repo["start"])

    def test_origin_is_bare_with_head_on_main(self):
        """origin/main and origin/HEAD exist, and nothing else is a remote (step 3)."""
        project, origin = self.plain.project, self.plain.origin
        self.assertEqual(git(origin, "rev-parse", "--is-bare-repository").strip(), "true")
        self.assertEqual(git(origin, "symbolic-ref", "HEAD").strip(), "refs/heads/main")
        self.assertEqual(git(project, "rev-parse", "origin/main").strip(), self.repo["start"])
        self.assertEqual(git(project, "symbolic-ref", "refs/remotes/origin/HEAD").strip(),
                         "refs/remotes/origin/main")
        self.assertEqual(git(project, "remote").split(), ["origin"])
        url = git(project, "remote", "get-url", "origin").strip()
        self.assertTrue(same_path(url, origin), url)

    def test_config_sets_line_ends_and_hooks_path(self):
        """core.autocrlf true and core.hooksPath .troy-mode/checks/git-hooks (step 5)."""
        for folder in (self.plain, self.review):
            with self.subTest(project=folder.root.name):
                get = git_proc(folder.project, "config", "--local", "--get", "core.autocrlf")
                self.assertEqual(get.stdout.strip(), "true")
                get = git_proc(folder.project, "config", "--local", "--get", "core.hooksPath")
                self.assertEqual(get.stdout.strip(), ".troy-mode/checks/git-hooks")

    def test_working_tree_has_crlf_line_ends(self):
        """Files committed with LF are checked out with CRLF, as in the pilot (step 5)."""
        data = (self.plain.project / "README.md").read_bytes()
        self.assertEqual(data, b"# wordcount\r\n\r\nCounts words.\r\n")

    def test_working_tree_is_clean(self):
        """git status lists nothing, so a snapshot can be taken."""
        for folder in (self.plain, self.review):
            with self.subTest(project=folder.root.name):
                self.assertEqual(git(folder.project, "status", "--porcelain").strip(), "")

    def test_review_patch_is_committed_with_the_title(self):
        """start.patch is applied on the start and committed with [start] title (step 2)."""
        project = self.review.project
        self.assertEqual(git(project, "symbolic-ref", "--short", "HEAD").strip(), BRANCH)
        self.assertEqual(git(project, "rev-parse", "HEAD^").strip(), self.repo["start"])
        self.assertEqual(git(project, "log", "-1", "--format=%s").strip(), TITLE)
        self.assertEqual(lf_text(git(project, "show", "HEAD:docs/review.md")),
                         "# Review\n\nRound one.\n")
        self.assertEqual(lf_text(git(project, "show", "HEAD:docs/notes.md")),
                         "# Notes\n\nFirst.\nSecond.\n")
        self.assertEqual(self.review_head, git(project, "rev-parse", "HEAD").strip())

    def test_review_branch_is_on_origin(self):
        """origin/<branch> is the round-1 head, as the main session would have pushed it."""
        project = self.review.project
        self.assertEqual(git(project, "rev-parse", f"origin/{BRANCH}").strip(), self.review_head)
        self.assertEqual(git(project, "rev-parse", "origin/main").strip(), self.repo["start"])

    def test_review_commit_did_not_run_the_project_hooks(self):
        """The project's pre-commit hook always fails, and the round-1 commit exists anyway."""
        hook = self.review.project / HOOK
        self.assertTrue(hook.is_file())
        self.assertIn("exit 1", lf_text(hook.read_bytes()))
        self.assertEqual(git(self.review.project, "log", "-1", "--format=%s").strip(), TITLE)


class CopyPluginTests(unittest.TestCase):
    """copy_plugin: a git archive of one version, without the folders roles never read."""

    @classmethod
    def setUpClass(cls):
        """A small plugin repository with two commits and an uncommitted change."""
        cls.repo = new_dir("plugin") / "tstack"
        cls.first = make_repo(cls.repo, {
            "agents/troy-developer.md": "# Developer\n\nFirst.\n",
            "troy-mode/flow/troyflow/brief.py": "VALUE = 1\n",
            "README.md": "# tstack\n",
            "docs/troy-mode/design/F16-role-exam.md": "# F16\n",
            ".github/workflows/troy-docs.yml": "name: docs\n",
            "troy-mode/dev/check_exam.py": "print(1)\n",
            "troy-mode/exam/troyexam/__init__.py": "X = 1\n",
            "troy-mode/exam/cases/dv-x/case.toml": 'id = "dv-x"\n',
        })
        cls.second = commit_files(cls.repo, {"agents/troy-developer.md":
                                             "# Developer\n\nSecond.\n"}, "Second")
        write_file(cls.repo, "agents/troy-developer.md", "# Developer\n\nNot committed.\n")

    def files_of(self, folder: Path) -> dict:
        """Every file of a folder: POSIX path to LF text."""
        return {p.relative_to(folder).as_posix(): lf_text(p.read_bytes())
                for p in folder.rglob("*") if p.is_file()}

    def test_the_copy_holds_the_commit_without_dev_docs_and_exam(self):
        """The committed files of the ref, not the working tree's; no docs/.github/dev/exam."""
        dest = new_dir("copy") / "tstack"
        commit = copy_plugin(self.repo, "HEAD", dest)
        self.assertEqual(commit, self.second)
        self.assertEqual(self.files_of(dest), {
            "agents/troy-developer.md": "# Developer\n\nSecond.\n",
            "troy-mode/flow/troyflow/brief.py": "VALUE = 1\n",
            "README.md": "# tstack\n"})

    def test_an_older_ref_gives_its_own_files(self):
        """The first commit's agent file, and its full ID."""
        dest = new_dir("copy") / "tstack"
        commit = copy_plugin(self.repo, self.first[:10], dest)
        self.assertEqual(commit, self.first)
        self.assertEqual(self.files_of(dest)["agents/troy-developer.md"],
                         "# Developer\n\nFirst.\n")


class GhStubTests(unittest.TestCase):
    """The gh stand-in of design 4.2 step 4 (contract ghstub.py)."""

    PR = {"number": 7, "title": TITLE, "body": "Writes the mock.\n\nCloses nothing."}

    @classmethod
    def setUpClass(cls):
        """A project with origin/main, a branch with one commit, and the stand-in in bin/."""
        top = new_dir("ghproj")
        origin = top / "wordcount.git"
        seed = top / "seed"
        cls.main_commit = make_repo(seed, {"README.md": "# wordcount\n",
                                           "src/wordcount/__init__.py": '"""Counts."""\n'})
        git(top, "clone", "-q", "--bare", str(seed), str(origin))
        cls.project = top / "wordcount"
        git(top, "clone", "-q", str(origin), str(cls.project))
        git(cls.project, "checkout", "-q", "-b", BRANCH)
        cls.head = commit_files(cls.project, {"src/wordcount/f01.py": "X = 1\nY = 2\n"}, TITLE)
        cls.bin = top / "bin"
        cls.bin.mkdir()
        write_gh(cls.bin, sys.executable, cls.PR)

    def gh(self, *args: str, python_flags=()) -> subprocess.CompletedProcess:
        """Runs gh.py in the project with this Python."""
        return subprocess.run([sys.executable, *python_flags, str(self.bin / "gh.py"), *args],
                              cwd=str(self.project), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                              timeout=60, check=False)

    def test_files_written(self):
        """gh, gh.cmd, gh.py, and pr.json; pr.json holds the PR."""
        for name in ("gh", "gh.cmd", "gh.py", "pr.json"):
            with self.subTest(file=name):
                self.assertTrue((self.bin / name).is_file())
        self.assertEqual(json.loads((self.bin / "pr.json").read_text(encoding="utf-8")), self.PR)
        self.assertTrue((self.bin / "gh").read_text(encoding="utf-8").startswith("#!/bin/sh"))

    def test_no_exam_word_in_any_file_it_writes(self):
        """The stand-in's text and messages are role-visible (design 6.1, 14.1 Blinding)."""
        for path in sorted(self.bin.iterdir()):
            with self.subTest(file=path.name):
                self.assertEqual(word_hits(path.read_text(encoding="utf-8")), [])

    def test_gh_py_needs_only_the_standard_library(self):
        """It runs isolated (-I), with no PYTHONPATH and no user site."""
        out = self.gh("pr", "view", "--json", "number", python_flags=("-I",))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), {"number": 7})

    def test_pr_view_text(self):
        """Without --json: title, state, number, url, base, head, then -- and the body."""
        out = self.gh("pr", "view")
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = lf_text(out.stdout).split("\n")
        self.assertTrue(any(line.startswith("title:") and TITLE in line for line in lines), lines)
        self.assertIn("state:\tOPEN", lines)
        self.assertTrue(any(line.startswith("number:") and "7" in line for line in lines), lines)
        self.assertTrue(any(line.startswith("url:") for line in lines), lines)
        self.assertIn("base:\tmain", lines)
        self.assertIn(f"head:\t{BRANCH}", lines)
        self.assertIn("--", lines)
        self.assertIn("Writes the mock.", "\n".join(lines[lines.index("--") + 1:]))

    def test_pr_view_json_fields(self):
        """Exactly the named fields, from the PR and the local branch."""
        out = self.gh("pr", "view", "--json",
                      "number,title,body,state,headRefName,baseRefName,headRefOid,isDraft")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), {
            "number": 7, "title": TITLE, "body": self.PR["body"], "state": "OPEN",
            "headRefName": BRANCH, "baseRefName": "main", "headRefOid": self.head,
            "isDraft": False})

    def test_pr_view_json_with_a_number_and_lists(self):
        """A PR number is accepted; files, commits, and the empty lists come from the branch."""
        out = self.gh("pr", "view", "7", "--json", "files,commits,comments,reviews,labels")
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual(set(data), {"files", "commits", "comments", "reviews", "labels"})
        self.assertEqual(data["files"], [{"path": "src/wordcount/f01.py", "additions": 2,
                                          "deletions": 0}])
        self.assertEqual([(c["oid"], c["messageHeadline"]) for c in data["commits"]],
                         [(self.head, TITLE)])
        self.assertEqual((data["comments"], data["reviews"], data["labels"]), ([], [], []))

    def test_pr_view_jq_prints_raw_strings(self):
        """--jq .title and -q .commits[].oid print raw values, one per line."""
        out = self.gh("pr", "view", "--json", "title", "--jq", ".title")
        self.assertEqual((out.returncode, lf_text(out.stdout)), (0, TITLE + "\n"))
        out = self.gh("pr", "view", "--json", "commits", "-q", ".commits[].oid")
        self.assertEqual((out.returncode, lf_text(out.stdout)), (0, self.head + "\n"))

    def test_unknown_json_field(self):
        """Exit 1 and gh's message."""
        out = self.gh("pr", "view", "--json", "title,bogus")
        self.assertEqual(out.returncode, 1)
        self.assertIn('Unknown JSON field: "bogus"', out.stderr)

    def test_pr_diff_is_the_branch_against_origin_main(self):
        """git diff origin/main...HEAD."""
        out = self.gh("pr", "diff")
        self.assertEqual(out.returncode, 0, out.stderr)
        expected = git(self.project, "diff", "origin/main...HEAD")
        self.assertEqual(lf_text(out.stdout), lf_text(expected))
        self.assertIn("+Y = 2", out.stdout)

    def test_pr_checks_reports_none(self):
        """Exit 1 with gh's message for a branch with no checks."""
        out = self.gh("pr", "checks")
        self.assertEqual(out.returncode, 1)
        self.assertIn(f"no checks reported on the '{BRANCH}' branch", out.stderr)
        self.assertEqual(out.stdout, "")

    def test_pr_comment_is_refused_and_changes_nothing(self):
        """Exit 1, the offline message, no output, and no change (design 14.2)."""
        before = (git(self.project, "status", "--porcelain"),
                  git(self.project, "rev-parse", "HEAD"),
                  (self.bin / "pr.json").read_bytes())
        out = self.gh("pr", "comment", "7", "--body", "Looks good.")
        self.assertEqual(out.returncode, 1)
        self.assertEqual(lf_text(out.stderr), OFFLINE)
        self.assertEqual(out.stdout, "")
        after = (git(self.project, "status", "--porcelain"),
                 git(self.project, "rev-parse", "HEAD"),
                 (self.bin / "pr.json").read_bytes())
        self.assertEqual(after, before)

    def test_every_other_command_is_refused(self):
        """Reviews, merges, edits, the API, issues, auth, and no arguments."""
        for args in (("pr", "review", "7", "--approve"), ("pr", "merge", "7", "--rebase"),
                     ("pr", "edit", "7", "--title", "x"), ("pr", "create", "--fill"),
                     ("api", "repos/ZJUCao/recipe-menu/pulls"), ("issue", "list"),
                     ("auth", "status"), ()):
            with self.subTest(args=args):
                out = self.gh(*args)
                self.assertEqual(out.returncode, 1)
                self.assertEqual(lf_text(out.stderr), OFFLINE)
                self.assertEqual(out.stdout, "")

    def test_offline_message(self):
        """The text gh prints when it cannot reach GitHub."""
        self.assertEqual(OFFLINE, "error connecting to api.github.com\n"
                                  "check your internet connection or https://githubstatus.com\n")

    def test_the_launcher_for_this_system_runs_gh_py(self):
        """gh.cmd on Windows, the sh script elsewhere (executable, so PATH finds it)."""
        if os.name == "nt":
            command = [str(self.bin / "gh.cmd"), "pr", "view", "--json", "number"]
        else:
            self.assertTrue(os.access(self.bin / "gh", os.X_OK))
            command = [str(self.bin / "gh"), "pr", "view", "--json", "number"]
        out = subprocess.run(command, cwd=str(self.project), capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, timeout=60, check=False)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), {"number": 7})


if __name__ == "__main__":
    unittest.main()
