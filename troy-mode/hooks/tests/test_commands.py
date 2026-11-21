"""Commands group (F05 design section 7, D43, and 13.1).

A subagent may run only read-only git and gh commands, plus any git command
except push in a scratch repository in the temp folder or the scratchpad.
Each allowed command must be silent and each refused one refused, alone and
inside the shell forms of design 7.1. For the main session, a call that cannot
be split is refused only when it holds a posting gh command (design 8.2, D200).
"""

import tempfile
import unittest
from pathlib import Path

from hook_helpers import (
    CR, DEV, EXPLORE, FOO, GP, HOOK_TEMP, IS_WINDOWS, MAIN, PAD, SCRATCH, SYSTEM_TEMP, TM,
    HookTestCase, Project, bash_call, git_bash_form, q, remove_tree, run_many, scratch_repo,
    start_call,
)

# Design 7.2, "Always".
ALWAYS_GIT = (
    "git status",
    "git status --porcelain=v1 -z --untracked-files=all",
    "git diff",
    "git diff HEAD -- src",
    "git log --oneline -5",
    "git show HEAD",
    "git blame src/pkg/app.py",
    "git grep -n run",
    "git rev-parse HEAD",
    "git rev-list --count HEAD",
    "git ls-files",
    "git ls-tree -r HEAD",
    "git cat-file -p HEAD",
    "git merge-base main feature",
    "git describe --always",
    "git shortlog -sn",
    "git for-each-ref refs/heads",
    "git show-ref",
    "git name-rev HEAD",
    "git check-ignore -v reports/junit.xml",
    "git check-attr -a README.md",
    "git var GIT_AUTHOR_IDENT",
    "git diff-tree --no-commit-id -r HEAD",
    "git diff-index HEAD",
    "git diff-files",
    "git count-objects -v",
    "git archive --format=tar HEAD",
    "git fetch origin",
    "git ls-remote origin",
    "git version",
    "git help log",
)

# Design 7.2, "Listing forms only" and "Working tree only".
LISTING_GIT = (
    "git branch",
    "git branch -a",
    "git branch -r",
    "git branch -v",
    "git branch --list",
    "git branch --show-current",
    "git tag",
    "git tag -l",
    "git tag --list",
    "git remote",
    "git remote -v",
    "git remote get-url origin",
    "git remote show origin",
    "git config --get user.email",
    "git config --get-all remote.origin.fetch",
    "git config --get-regexp ^user",
    "git config --list",
    "git config user.email",
    "git stash list",
    "git stash show",
    "git stash show -p",
    "git worktree list",
    "git reflog",
    "git reflog show",
    "git restore src/pkg/app.py",
    "git restore -- tests/test_app.py",
    "git restore .",
    "git restore --worktree src/pkg/app.py",
)

# Design 7.2, every other git command, with the "git <subcommand>" fragment
# the reason must hold (contract 3).
REFUSED_GIT = (
    ("git commit -m 'Add x'", "git commit"),
    ("git commit --amend --no-edit", "git commit"),
    ("git push origin feature", "git push"),
    ("git add -A", "git add"),
    ("git add src/pkg/app.py", "git add"),
    ("git rm src/pkg/app.py", "git rm"),
    ("git mv src/pkg/app.py src/pkg/main.py", "git mv"),
    ("git reset --hard HEAD~1", "git reset"),
    ("git reset src/pkg/app.py", "git reset"),
    ("git switch main", "git switch"),
    ("git switch -c topic", "git switch"),
    ("git checkout main", "git checkout"),
    ("git checkout -- src/pkg/app.py", "git checkout"),
    ("git merge main", "git merge"),
    ("git rebase main", "git rebase"),
    ("git cherry-pick 1234abcd", "git cherry-pick"),
    ("git revert HEAD", "git revert"),
    ("git am fix.patch", "git am"),
    ("git apply fix.patch", "git apply"),
    ("git clean -fdx", "git clean"),
    ("git update-ref refs/heads/main HEAD", "git update-ref"),
    ("git pull", "git pull"),
    ("git gc", "git gc"),
    ("git init", "git init"),
    ("git notes add -m note", "git notes"),
    ("git submodule update --init", "git submodule"),
    ("git branch topic", "git branch"),
    ("git branch -d old", "git branch"),
    ("git branch -D old", "git branch"),
    ("git branch -m old new", "git branch"),
    ("git tag v1.0", "git tag"),
    ("git tag -a v1.0 -m 'Release'", "git tag"),
    ("git tag -d v1.0", "git tag"),
    ("git remote add upstream https://example.test/x.git", "git remote"),
    ("git remote remove origin", "git remote"),
    ("git remote set-url origin https://example.test/y.git", "git remote"),
    ("git config user.email someone@example.test", "git config"),
    ("git config --unset user.email", "git config"),
    ("git config --global user.name Someone", "git config"),
    ("git config --add x.y z", "git config"),
    ("git stash", "git stash"),
    ("git stash push -m wip", "git stash"),
    ("git stash pop", "git stash"),
    ("git stash apply", "git stash"),
    ("git stash drop", "git stash"),
    ("git worktree add ../wt", "git worktree"),
    ("git worktree remove wt", "git worktree"),
    ("git reflog expire --expire=now --all", "git reflog"),
    ("git reflog delete HEAD@{1}", "git reflog"),
    ("git restore --staged src/pkg/app.py", "git restore"),
    ("git restore -S src/pkg/app.py", "git restore"),
    ("git restore --source HEAD~1 src/pkg/app.py", "git restore"),
    ("git restore --source=HEAD~1 src/pkg/app.py", "git restore"),
    ("git restore -s HEAD~1 src/pkg/app.py", "git restore"),
    ("git restore --staged --worktree src/pkg/app.py", "git restore"),
)

# Design 7.2, global options before the subcommand, and design 7.1, program forms.
GLOBAL_ALLOWED = (
    "git -C . status",
    "git -C src log -1",
    "git --no-pager log -1",
    "git -c color.ui=never diff",
    "git --git-dir=.git status",
    "git --no-pager -C . show HEAD",
    "/usr/bin/git status",
    "git.exe status",
    "'/c/Program Files/Git/cmd/git.exe' log -1",
    "/usr/bin/gh pr view 1",
    "gh.exe pr list",
)
GLOBAL_REFUSED = (
    ("git -C . commit -m x", "git commit"),
    ("git -C src push", "git push"),
    ("git --no-pager commit -m x", "git commit"),
    ("git -c user.name=Someone commit -m x", "git commit"),
    ("git --git-dir=.git --work-tree=. commit -m x", "git commit"),
    ("/usr/bin/git commit -m x", "git commit"),
    ("git.exe commit -m x", "git commit"),
    ("'/c/Program Files/Git/cmd/git.exe' commit -m x", "git commit"),
    ("C:/Git/cmd/git.exe push", "git push"),
    ("/usr/bin/gh pr comment 1 --body ok", "gh pr comment"),
    ("gh.exe pr comment 1 --body ok", "gh pr comment"),
)

# Design 7.3.
ALLOWED_GH = (
    "gh pr view 12",
    "gh pr view 12 --json title,body",
    "gh pr diff 12",
    "gh pr list",
    "gh pr list --state open",
    "gh pr checks 12",
    "gh pr status",
    "gh issue view 3",
    "gh issue list",
    "gh issue status",
    "gh repo view",
    "gh run view 5",
    "gh run list",
    "gh release view v1.0",
    "gh release list",
    "gh search prs counting",
    "gh status",
    "gh auth status",
    "gh api repos/o/r/pulls/12/comments",
    "gh api -X GET repos/o/r",
    "gh api --method GET repos/o/r",
    "gh api --paginate repos/o/r/pulls --jq '.[].number'",
    "gh api -H 'Accept: application/vnd.github+json' repos/o/r/pulls",
)
REFUSED_GH = (
    ("gh pr comment 12 --body 'Looks good'", "gh pr comment"),
    ("gh pr create --title 'Add x' --body 'Body'", "gh pr create"),
    ("gh pr merge 12 --squash", "gh pr merge"),
    ("gh pr edit 12 --title 'New'", "gh pr edit"),
    ("gh pr review 12 --approve", "gh pr review"),
    ("gh pr close 12", "gh pr close"),
    ("gh pr ready 12", "gh pr ready"),
    ("gh pr checkout 12", "gh pr checkout"),
    ("gh issue create --title x --body y", "gh issue create"),
    ("gh issue comment 3 --body x", "gh issue comment"),
    ("gh issue close 3", "gh issue close"),
    ("gh repo create o/new --private", "gh repo create"),
    ("gh repo clone o/r", "gh repo clone"),
    ("gh release create v1.0", "gh release create"),
    ("gh run rerun 5", "gh run rerun"),
    ("gh workflow run ci.yml", "gh workflow run"),
    ("gh auth login", "gh auth login"),
    ("gh secret set TOKEN", "gh secret set"),
    ("gh browse", "gh browse"),
    ("gh api -X POST repos/o/r/issues", "gh api"),
    ("gh api --method POST repos/o/r/issues", "gh api"),
    ("gh api --method=PATCH repos/o/r/issues/1", "gh api"),
    ("gh api -X DELETE repos/o/r/issues/1/labels", "gh api"),
    ("gh api repos/o/r/issues -f title=x", "gh api"),
    ("gh api repos/o/r/issues -F number=1", "gh api"),
    ("gh api repos/o/r/issues --field title=x", "gh api"),
    ("gh api repos/o/r/issues --raw-field title=x", "gh api"),
    ("gh api repos/o/r/issues --input body.json", "gh api"),
    ("gh api graphql -f query='query { viewer { login } }'", "gh api"),
)

# Commands that are neither git nor gh; a role may run them (writes through
# Bash are caught after the call, design section 6).
OTHER_COMMANDS = (
    "ls -la",
    "python -m pytest -q",
    "cat src/pkg/app.py | grep run",
    "mkdir -p build && cp src/pkg/app.py build/",
    "echo hi > /tmp/troyhook-notes.txt",
    "python -c \"print('git')\"",
)

# The shell forms of design 7.1 and 13.1, as templates around a command.
WRAPPERS = (
    ("alone", "{c}"),
    ("after ;", "echo start; {c}"),
    ("before ;", "{c}; echo done"),
    ("after &&", "ls && {c}"),
    ("after ||", "false || {c}"),
    ("after |", "echo y | {c}"),
    ("before |", "{c} | cat"),
    ("after &", "true & {c}"),
    ("after a line break", "echo start\n{c}"),
    ("in ( )", "({c})"),
    ("in $( )", 'echo "$({c})"'),
    ("in backticks", "echo `{c}`"),
    ("in bash -c", 'bash -c "{c}"'),
    ("in sh -c", "sh -c '{c}'"),
    ("in eval", 'eval "{c}"'),
    ("after assignments", "FOO=1 BAR=two {c}"),
    ("after env", "env {c}"),
    ("after env with an assignment", "env GIT_PAGER=cat {c}"),
    ("after command", "command {c}"),
    ("after exec", "exec {c}"),
    ("after nohup", "nohup {c}"),
    ("after time", "time {c}"),
    ("after timeout", "timeout 60 {c}"),  # D223: timeout is a wrapper
    ("after timeout with options", "timeout -k 5 --signal=TERM 60 {c}"),
    ("after xargs", "echo HEAD | xargs {c}"),
    ("after cd into the project", "cd src && {c}"),
)
REFUSED_SAMPLES = (("git commit -m x", "git commit"), ("git push origin feature", "git push"),
                   ("gh pr comment 1 --body ok", "gh pr comment"))
ALLOWED_SAMPLES = ("git status", "git log --oneline -3", "gh pr view 1")

HEREDOC_ALLOWED = (
    "cat > notes.txt <<'EOF'\ngit commit -m 'Add x'\ngh pr comment 1 --body ok\nEOF",
    "cat > notes.txt <<EOF\ngit push origin main\nEOF",
    "cat > notes.txt <<-EOF\n\tgit commit -m x\n\tEOF",
    # A heredoc that feeds a script file, which is then run (13.1). Not
    # python - <<'PY', which R23 refuses (design 8.3, D223).
    "cat > build/heredoc_check.py <<'PY'\nprint('git commit -m x')\nPY\n"
    "python build/heredoc_check.py\ngit status",
    "cat > tests/test_new.py <<'EOF'\ndef test_x():\n"
    "    assert \"git commit\" in \"git commit -m x\"\nEOF",
)
HEREDOC_REFUSED = (
    ("cat > notes.txt <<'EOF'\ngit status\nEOF\ngit commit -m real", "git commit"),
    ("cat > notes.txt <<'EOF' && git push origin feature\nhello\nEOF", "git push"),
)
UNBALANCED_REFUSED = (
    'git commit -m "unfinished',
    "echo 'start; git push origin feature",
    'gh pr comment 1 --body "half',
)

# Design 8.2 and 7.1 (D200): main-session calls that cannot be split.
MAIN_UNBALANCED_POSTING = (
    'gh pr comment 1 --body "half',
    'gh issue create --title "Add x',
    "echo 'start; gh issue comment 3 --body ok",
    'gh release create v1.0 --notes "half',
)
MAIN_UNBALANCED_OTHER = (
    'gh pr view 1 --json "title',
    "echo 'start; gh pr view 1",
    'echo "Works with Claude',
)


class CommandTestCase(HookTestCase):
    """Runs tables of commands for one caller and checks each answer."""

    caller = DEV

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts the roles the tests use."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, c) for c in (DEV, CR, TM)])

    def check_allowed(self, commands, caller=None, **kwargs):
        """Asserts that every command is silent."""
        caller = caller or self.caller
        outs = run_many([bash_call(self.project, caller, c, **kwargs) for c in commands])
        for command, out in zip(commands, outs):
            with self.subTest(caller=caller.label, command=command):
                self.assert_silent(out)

    def check_refused(self, cases, caller=None, main_session_words=True, **kwargs):
        """Asserts that every (command, fragment) is refused with the fragment."""
        caller = caller or self.caller
        outs = run_many([bash_call(self.project, caller, c, **kwargs) for c, _ in cases])
        for (command, fragment), out in zip(cases, outs):
            with self.subTest(caller=caller.label, command=command):
                fragments = (fragment,)
                if main_session_words and fragment.startswith("git "):
                    fragments += ("main session",)
                self.assert_denied(out, *fragments)


class GitCommandTests(CommandTestCase):
    """Design 7.2 for a role."""

    def test_always_allowed_git_commands_pass(self):
        """Each command of the "Always" row is silent."""
        self.check_allowed(ALWAYS_GIT)

    def test_listing_and_working_tree_forms_pass(self):
        """The listing forms and git restore without --staged or --source are silent."""
        self.check_allowed(LISTING_GIT)

    def test_other_git_commands_are_refused(self):
        """Every other git command is refused with git <subcommand> and "main session".

        Planted bug caught: commit in the allowed git commands (13.2).
        """
        self.check_refused(REFUSED_GIT)

    def test_global_options_and_program_forms(self):
        """-C, -c, --no-pager, --git-dir, and paths to git or gh are read through."""
        self.check_allowed(GLOBAL_ALLOWED)
        self.check_refused(GLOBAL_REFUSED)

    def test_other_commands_pass(self):
        """Commands that are neither git nor gh are silent before the call."""
        self.check_allowed(OTHER_COMMANDS)

    def test_powershell_is_read_the_same_way(self):
        """PowerShell's git commit is refused; git status and a ; list of reads pass."""
        self.check_allowed(("git status", "git status; git log -1"), tool="PowerShell")
        self.check_refused((("git commit -m x", "git commit"),
                            ("git status; git commit -m x", "git commit")), tool="PowerShell")


class GhCommandTests(CommandTestCase):
    """Design 7.3 for a role."""

    def test_allowed_gh_commands_pass(self):
        """Each read-only gh command, and gh api with GET only, is silent."""
        self.check_allowed(ALLOWED_GH)

    def test_other_gh_commands_are_refused(self):
        """Every other gh command, and gh api with a method or fields, is refused."""
        self.check_refused(REFUSED_GH)


class ShellFormTests(CommandTestCase):
    """Design 7.1: refused commands are found inside every shell form."""

    def test_refused_commands_inside_every_form(self):
        """git commit, git push, and gh pr comment are refused in each form, timeout's included."""
        cases = [(name, template.replace("{c}", command), fragment)
                 for name, template in WRAPPERS for command, fragment in REFUSED_SAMPLES]
        outs = run_many([bash_call(self.project, DEV, c) for _, c, _ in cases])
        for (name, command, fragment), out in zip(cases, outs):
            with self.subTest(form=name, command=command):
                self.assert_denied(out, fragment)

    def test_allowed_commands_inside_every_form(self):
        """Pair: git status, git log, and gh pr view are silent in each form."""
        cases = [(name, template.replace("{c}", command))
                 for name, template in WRAPPERS for command in ALLOWED_SAMPLES]
        outs = run_many([bash_call(self.project, DEV, c) for _, c in cases])
        for (name, command), out in zip(cases, outs):
            with self.subTest(form=name, command=command):
                self.assert_silent(out)

    def test_heredoc_bodies_are_not_commands(self):
        """Text such as "git commit" inside a heredoc body passes, also in a script then run."""
        self.check_allowed(HEREDOC_ALLOWED)

    def test_commands_around_a_heredoc_are_still_read(self):
        """Pair: a git write after the body, or on the heredoc's own line, is refused."""
        self.check_refused(HEREDOC_REFUSED)

    def test_unbalanced_quote_around_a_git_write_is_refused(self):
        """A command that cannot be split is refused when its text holds a git or gh write."""
        outs = run_many([bash_call(self.project, DEV, c) for c in UNBALANCED_REFUSED])
        for command, out in zip(UNBALANCED_REFUSED, outs):
            with self.subTest(command=command):
                self.assert_denied(out)


class MainSessionUnparsedTests(HookTestCase):
    """D200: a main-session call that cannot be split is refused when it holds a posting gh command."""

    @classmethod
    def setUpClass(cls):
        """Builds one strict project."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)

    def test_unbalanced_quote_around_a_posting_command_is_refused(self):
        """gh pr comment, gh issue create, gh issue comment, or gh release create: rule unparsed."""
        for command in MAIN_UNBALANCED_POSTING:
            with self.subTest(command=command):
                before = len(self.project.log_lines())
                out = bash_call(self.project, MAIN, command).run()
                self.assert_denied(out, msg=command)
                lines = self.project.log_lines()[before:]
                self.assertEqual(1, len(lines), f"expected one new log line: {lines}")
                self.assertEqual(("unparsed", "deny", None),
                                 (lines[0]["rule"], lines[0]["decision"], lines[0]["agent_id"]))

    def test_unbalanced_quote_without_a_posting_command_passes(self):
        """Pair: an unbalanced quote around gh pr view, or around plain text, is silent."""
        for command in MAIN_UNBALANCED_OTHER:
            with self.subTest(command=command):
                self.assert_silent(bash_call(self.project, MAIN, command).run(), msg=command)


class OtherCallerCommandTests(CommandTestCase):
    """The Code Reviewer, the Test Manager, and subagents that are not roles get the same limits."""

    def test_read_only_commands_pass_for_every_subagent(self):
        """git status, git diff, git log, and gh pr view are silent for each."""
        for caller in (CR, TM, GP, EXPLORE, FOO):
            self.check_allowed(("git status", "git diff", "git log -1", "gh pr view 1"),
                               caller=caller)

    def test_writes_are_refused_for_every_subagent(self):
        """git commit, git push, and gh pr comment are refused for each."""
        for caller in (CR, TM, GP, EXPLORE, FOO):
            self.check_refused(REFUSED_SAMPLES, caller=caller)


class ScratchRepositoryTests(CommandTestCase):
    """Design 7.2: any git command but push in a scratch repository in temp or the scratchpad."""

    @classmethod
    def setUpClass(cls):
        """Adds a scratch repository in the hook's temp folder and one in the scratchpad."""
        super().setUpClass()
        cls.scratch = scratch_repo(HOOK_TEMP)
        cls.pad_repo = scratch_repo(PAD)
        # A scratch repository that /tmp/<name>/repo names: in the system temp
        # folder on Windows, where Git Bash's /tmp points, and in /tmp elsewhere.
        tmp = Path(tempfile.mkdtemp(prefix="troyhook-tmp-",
                                    dir=str(SYSTEM_TEMP) if IS_WINDOWS else "/tmp")).resolve()
        cls.addClassCleanup(remove_tree, tmp)
        cls.tmp_repo = scratch_repo(tmp, "repo")
        cls.tmp_repo_name = f"{tmp.name}/repo"

    def test_git_writes_in_a_scratch_repository_pass(self):
        """git -C <temp> commit, cd <temp> && git commit, and --git-dir forms are silent."""
        s, project = q(self.scratch), q(self.project.root)
        commands = (
            f"git -C {s} commit -m 'Scratch'",
            f"git -C {s} add -A && git -C {s} commit -m 'Scratch'",
            f"cd {s} && git add -A && git commit -m 'Scratch'",
            f"cd {s} && git reset --hard HEAD",
            f"git --git-dir={q(self.scratch / '.git')} --work-tree={s} commit -m 'Scratch'",
            f"git -C {s} checkout -b check",
            f"cd {project} && git status && cd {s} && git commit -m 'Scratch'",
        )
        for caller in (TM, DEV):
            self.check_allowed(commands, caller=caller)

    def test_scratchpad_repository_passes(self):
        """A repository in the session's scratchpad counts as a scratch repository."""
        self.check_allowed((f"git -C {q(self.pad_repo)} commit -m 'Scratch'",), caller=TM,
                           scratchpad=PAD)

    def test_push_from_a_scratch_repository_is_refused(self):
        """git -C <temp> push and cd <temp> && git push are refused: a clone can push."""
        s = q(self.scratch)
        self.check_refused(((f"git -C {s} push", "git push"),
                            (f"git -C {s} push origin feature", "git push"),
                            (f"cd {s} && git push", "git push")), caller=TM)

    def test_project_is_not_a_scratch_repository(self):
        """git -C <project> commit and a cd back into the project are refused.

        Planted bug caught: a scratch repository test that accepts the project
        (13.2). On Linux the project lies in /tmp, a temp folder;
        ProjectInTempCommandTests covers every platform.
        """
        s, project = q(self.scratch), q(self.project.root)
        self.check_refused((
            (f"git -C {project} commit -m x", "git commit"),
            (f"git -C {q(self.project.path('src'))} commit -m x", "git commit"),
            (f"cd {project} && git commit -m x", "git commit"),
            (f"cd {s} && git commit -m 'Scratch' && cd {project} && git commit -m x",
             "git commit"),
            (f"git --git-dir={q(self.project.git_dir)} --work-tree={project} commit -m x",
             "git commit"),
        ), caller=TM)

    def test_core_hooks_path_option_is_refused_in_a_scratch_repository(self):
        """-c core.hooksPath= is refused for every caller and every repository (design 8.2)."""
        s = q(self.scratch)
        outs = run_many([bash_call(self.project, TM, f"git -C {s} -c core.hooksPath=/dev/null "
                                                     "commit -m x"),
                         bash_call(self.project, DEV, "git -c core.hooksPath=/dev/null status")])
        for out in outs:
            self.assert_denied(out)

    @unittest.skipUnless(IS_WINDOWS, "a sibling of the temp folder is in /tmp on Linux")
    def test_sibling_of_the_temp_folder_is_not_scratch_on_windows(self):
        """<temp>-other is not the temp folder, so a commit there is refused."""
        sibling = q(Path(str(HOOK_TEMP) + "-other") / "repo")
        self.check_refused(((f"git -C {sibling} commit -m x", "git commit"),), caller=TM)

    def test_tmp_other_is_not_scratch(self):
        """/tmp-other/repo is not in /tmp, so a commit there is refused; /tmp/repo passes.

        On Windows these are Git Bash forms, with the system temp folder as the
        hook's temp folder (convention 7).
        Planted bug caught: a temp folder test that accepts /tmp-other (13.2).
        """
        self.check_refused((("git -C /tmp-other/repo commit -m x", "git commit"),), caller=TM,
                           temp=SYSTEM_TEMP)
        self.check_allowed((f"git -C /tmp/{self.tmp_repo_name} commit -m 'Scratch'",),
                           caller=TM, temp=SYSTEM_TEMP)

    @unittest.skipUnless(IS_WINDOWS, "Git Bash path forms")
    def test_git_bash_forms_name_the_scratch_repository(self):
        """git -C /c/.../scratch commit and cd /c/.../scratch && git commit are silent."""
        s = q(git_bash_form(self.scratch))
        self.check_allowed((f"git -C {s} commit -m 'Scratch'",
                            f"cd {s} && git commit -m 'Scratch'"), caller=TM)
        self.check_refused(((f"git -C {s} push", "git push"),), caller=TM)


class ProjectInTempCommandTests(HookTestCase):
    """A project in the temp folder is never a scratch repository.

    The hook's temp variables point at the project's parent folder.
    Planted bug caught: a scratch repository test that accepts the project (13.2).
    """

    @classmethod
    def setUpClass(cls):
        """Builds a project and a scratch repository in one folder used as temp."""
        cls.temp = SCRATCH / "projtemp-commands"
        cls.temp.mkdir(exist_ok=True)
        cls.project = Project(parent=cls.temp)
        cls.addClassCleanup(cls.project.close)
        cls.scratch = scratch_repo(cls.temp)
        run_many([start_call(cls.project, c) for c in (DEV, TM)])

    def run_cmd(self, command, caller=TM):
        """Runs a Bash call with the project's parent as temp folder."""
        return bash_call(self.project, caller, command, temp=self.temp).run()

    def test_git_writes_in_the_project_are_refused(self):
        """git commit with no -C, with -C, after cd, and with --git-dir all name the project."""
        project = q(self.project.root)
        commands = ("git commit -m x", f"git -C {project} commit -m x",
                    f"cd {project} && git commit -m x",
                    f"git -C {q(self.project.path('src'))} commit -m x",
                    f"git --git-dir={q(self.project.git_dir)} --work-tree={project} commit -m x")
        for caller in (TM, DEV):
            for command in commands:
                with self.subTest(caller=caller.label, command=command):
                    self.assert_denied(self.run_cmd(command, caller), "git commit",
                                       "main session")

    def test_scratch_repository_beside_the_project_passes(self):
        """Pair: a commit in the scratch repository beside the project is silent."""
        s = q(self.scratch)
        self.assert_silent(self.run_cmd(f"git -C {s} commit -m 'Scratch'"))
        self.assert_silent(self.run_cmd(f"cd {s} && git commit -m 'Scratch'"))
        self.assert_denied(self.run_cmd(f"git -C {s} push"), "git push")


if __name__ == "__main__":
    unittest.main()
