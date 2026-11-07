"""Guards group (F05 design 8.2, D44, and 13.1).

For every caller, the main session included, the PreToolUse hook refuses
skipping the git hooks, changing core.hooksPath, committing while the hooks
are off, opening a PR from main (R21), and a PR title or description with
attribution (R19). The tests run as the main session unless they say
otherwise, and check the refusal's rule in the log (convention 14).
"""

import unittest

from hook_helpers import (
    ATTRIBUTION_LINE, DEV, GIT_HOOK_NAMES, HOOKS_PATH, MAIN, TRAILER, HookTestCase, Project,
    bash_call, make_config, start_call,
)

HEREDOC_BODY = (
    "gh pr create --title 'Add word counting' --body \"$(cat <<'EOF'\n"
    "## Why\n\nCount words.\n\n{line}\nEOF\n)\""
)


class GuardTestCase(HookTestCase):
    """Runs main-session Bash calls on a class-wide project."""

    project = None

    def run_main(self, command, project=None):
        """Runs a main-session Bash PreToolUse call."""
        return bash_call(project or self.project, MAIN, command).run()

    def assert_refused_by(self, command, rule, *fragments, project=None):
        """Asserts a main-session refusal whose last log line has the rule."""
        project = project or self.project
        out = self.run_main(command, project)
        self.assert_denied(out, *fragments, msg=command)
        self.assert_last_log(project, msg=command, rule=rule, decision="deny", agent_id=None,
                             event="PreToolUse", tool="Bash")


class NoVerifyTests(GuardTestCase):
    """--no-verify and commit -n are refused; push -n is a dry run."""

    @classmethod
    def setUpClass(cls):
        """Builds a project with the git hooks on, on branch feature."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)

    def test_commit_with_no_verify_or_n_is_refused(self):
        """git commit --no-verify and git commit -n are refused for the main session."""
        for command in ("git commit --no-verify -m 'Add x'", "git commit -n -m 'Add x'",
                        "git commit -m 'Add x' --no-verify",
                        "git add -A && git commit --no-verify -m 'Add x'"):
            with self.subTest(command=command):
                self.assert_refused_by(command, "no-verify", "-n")

    def test_push_merge_am_rebase_with_no_verify_are_refused(self):
        """git push, merge, am, and rebase with --no-verify are refused."""
        for command in ("git push --no-verify origin feature", "git merge --no-verify topic",
                        "git am --no-verify fix.patch", "git rebase --no-verify main"):
            with self.subTest(command=command):
                self.assert_refused_by(command, "no-verify", "--no-verify")

    def test_plain_commit_push_and_push_dry_run_pass(self):
        """Pair: git commit, git push, git push -n, and git merge are silent with the hooks on."""
        for command in ("git commit -m 'Add x'", "git push origin feature",
                        "git push -n origin feature", "git push --dry-run origin feature",
                        "git merge topic"):
            with self.subTest(command=command):
                self.assert_silent(self.run_main(command))

    def test_core_hooks_path_option_is_refused_for_a_role(self):
        """The guards apply to roles too: a role's git -c core.hooksPath= status is refused."""
        start_call(self.project, DEV).run()
        out = bash_call(self.project, DEV, "git -c core.hooksPath=/dev/null status").run()
        self.assert_denied(out)
        self.assert_silent(bash_call(self.project, DEV, "git status").run())


class HooksPathTests(GuardTestCase):
    """-c core.hooksPath= and git config core.hooksPath are refused."""

    @classmethod
    def setUpClass(cls):
        """Builds a project with the git hooks on."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)

    def test_core_hooks_path_option_is_refused(self):
        """-c core.hooksPath=... before any subcommand is refused."""
        for command in ("git -c core.hooksPath=/dev/null commit -m x",
                        "git -c core.hooksPath= commit -m x",
                        "git -c core.hooksPath=.githooks push origin feature",
                        "git -c core.hooksPath=/dev/null status"):
            with self.subTest(command=command):
                self.assert_refused_by(command, "hooks-path")

    def test_setting_or_unsetting_core_hooks_path_is_refused(self):
        """git config that sets or unsets core.hooksPath is refused."""
        for command in ("git config core.hooksPath .githooks",
                        "git config --local core.hooksPath /dev/null",
                        "git config --unset core.hooksPath",
                        "git config --global core.hooksPath /dev/null"):
            with self.subTest(command=command):
                self.assert_refused_by(command, "hooks-path")

    def test_reading_core_hooks_path_passes(self):
        """Pair: reading core.hooksPath and setting another key are silent."""
        for command in ("git config --get core.hooksPath", "git config core.hooksPath",
                        "git -c color.ui=never commit -m x", "git config user.name 'Troy'"):
            with self.subTest(command=command):
                self.assert_silent(self.run_main(command))


class HooksOffTests(GuardTestCase):
    """Commits, merges, and pushes are refused while the git hooks are off."""

    def check_off(self, project):
        """Asserts commit, merge, and push are refused and reads pass, in one project."""
        for command in ("git commit -m 'Add x'", "git merge topic", "git push origin feature"):
            with self.subTest(command=command):
                self.assert_refused_by(command, "hooks-off", "core.hooksPath", project=project)
        for command in ("git status", "git log -1", "git checkout -b topic"):
            with self.subTest(command=command):
                self.assert_silent(self.run_main(command, project))

    def test_unset_hooks_path_refuses_commit(self):
        """With core.hooksPath unset, the reason says how to turn the hooks on."""
        project = Project(hooks_on=False)
        self.addCleanup(project.close)
        self.check_off(project)

    def test_other_hooks_path_refuses_commit(self):
        """With core.hooksPath set to another folder, commit is refused."""
        project = Project(hooks_on=False)
        self.addCleanup(project.close)
        project.git("config", "core.hooksPath", ".githooks")
        self.check_off(project)

    def test_missing_hook_files_refuse_commit(self):
        """With core.hooksPath right but the hook files gone, commit is refused."""
        project = Project()
        self.addCleanup(project.close)
        for name in GIT_HOOK_NAMES:
            project.delete(f"{HOOKS_PATH}/{name}")
        self.check_off(project)

    def test_hooks_on_lets_commit_pass(self):
        """Pair: the same commands are silent with the hooks on."""
        project = Project()
        self.addCleanup(project.close)
        for command in ("git commit -m 'Add x'", "git merge topic", "git push origin feature"):
            with self.subTest(command=command):
                self.assert_silent(self.run_main(command, project))


class PrFromMainTests(GuardTestCase):
    """R21: gh pr create from main is refused."""

    @classmethod
    def setUpClass(cls):
        """Builds a project on main and one on branch feature."""
        cls.on_main = Project(branch=None)
        cls.on_feature = Project()
        cls.addClassCleanup(cls.on_main.close)
        cls.addClassCleanup(cls.on_feature.close)

    def test_create_on_main_is_refused(self):
        """With main checked out and no --head, gh pr create is refused with R21."""
        self.assert_refused_by("gh pr create --title 'Add word counting' --body 'Counts words.'",
                               "pr-from-main", "R21", project=self.on_main)

    def test_create_with_head_main_is_refused(self):
        """On a branch, --head main and -H main are refused with R21."""
        for command in ("gh pr create --head main --title 'Add x' --body 'Body.'",
                        "gh pr create -H main --title 'Add x' --body 'Body.'"):
            with self.subTest(command=command):
                self.assert_refused_by(command, "pr-from-main", "R21", project=self.on_feature)

    def test_create_on_a_branch_passes(self):
        """Pair: on a branch, gh pr create, with or without --base main, is silent."""
        for command in ("gh pr create --title 'Add word counting' --body 'Counts words.'",
                        "gh pr create --base main --title 'Add x' --body 'Body.'",
                        "gh pr create --head feature --title 'Add x' --body 'Body.'"):
            with self.subTest(command=command):
                self.assert_silent(self.run_main(command, self.on_feature))

    def test_create_on_main_with_another_head_passes(self):
        """Pair: on main, --head feature names another branch and is silent."""
        out = self.run_main("gh pr create --head feature --title 'Add x' --body 'Body.'",
                            self.on_main)
        self.assert_silent(out)


class AttributionTests(GuardTestCase):
    """R19: gh pr create and gh pr edit with attribution are refused."""

    @classmethod
    def setUpClass(cls):
        """Builds a strict project and a trailers project, with body files."""
        cls.project = Project()
        cls.trailers = Project(config=make_config(mode="trailers"))
        for project in (cls.project, cls.trailers):
            cls.addClassCleanup(project.close)
            project.write("pr-body-good.md", "## Why\n\nCount words.\n")
            project.write("pr-body-bad.md", f"## Why\n\nCount words.\n\n{ATTRIBUTION_LINE}\n")

    def test_generated_with_line_in_body_is_refused(self):
        """A --body with the "Generated with Claude Code" line is refused with R19."""
        command = f"gh pr create --title 'Add x' --body 'Count words.\n\n{ATTRIBUTION_LINE}'"
        self.assert_refused_by(command, "attribution", "R19")

    def test_generated_with_line_in_heredoc_body_is_refused(self):
        """The line inside a heredoc that builds --body is still found (command text)."""
        self.assert_refused_by(HEREDOC_BODY.format(line=ATTRIBUTION_LINE), "attribution", "R19")

    def test_clean_heredoc_body_passes(self):
        """Pair: the same heredoc without the line is silent."""
        self.assert_silent(self.run_main(HEREDOC_BODY.format(line="Thanks.")))

    def test_body_file_with_the_line_is_refused(self):
        """--body-file naming a file with the line is refused with R19."""
        self.assert_refused_by("gh pr create --title 'Add x' --body-file pr-body-bad.md",
                               "attribution", "R19")

    def test_clean_body_file_passes(self):
        """Pair: a clean --body-file is silent."""
        self.assert_silent(self.run_main("gh pr create --title 'Add x' --body-file "
                                         "pr-body-good.md"))

    def test_pr_edit_with_trailer_is_refused(self):
        """gh pr edit whose body holds a Co-Authored-By: Claude trailer is refused."""
        self.assert_refused_by(f"gh pr edit 7 --body 'Fix.\n\n{TRAILER}'", "attribution", "R19")
        self.assert_refused_by("gh pr edit 7 --body-file pr-body-bad.md", "attribution", "R19")

    def test_pr_edit_without_attribution_passes(self):
        """Pair: gh pr edit with a plain title is silent."""
        self.assert_silent(self.run_main("gh pr edit 7 --title 'Fix the counter'"))

    def test_word_claude_is_refused_in_strict_mode(self):
        """In strict mode, a title or body with the word Claude is refused."""
        self.assert_refused_by("gh pr create --title 'Support Claude models' --body 'Plain.'",
                               "attribution", "R19")
        self.assert_refused_by("gh pr create --title 'Add x' --body 'Works with Claude.'",
                               "attribution", "R19")

    def test_word_claude_passes_in_trailers_mode(self):
        """In trailers mode, the bare word Claude is silent."""
        for command in ("gh pr create --title 'Support Claude models' --body 'Plain.'",
                        "gh pr create --title 'Add x' --body 'Works with Claude.'"):
            with self.subTest(command=command):
                self.assert_silent(self.run_main(command, self.trailers))

    def test_trailers_mode_still_refuses_attribution_lines(self):
        """In trailers mode, the "Generated with" line and its body file are refused."""
        command = f"gh pr create --title 'Add x' --body 'Count words.\n\n{ATTRIBUTION_LINE}'"
        self.assert_refused_by(command, "attribution", "R19", project=self.trailers)
        self.assert_refused_by("gh pr create --title 'Add x' --body-file pr-body-bad.md",
                               "attribution", "R19", project=self.trailers)


if __name__ == "__main__":
    unittest.main()
