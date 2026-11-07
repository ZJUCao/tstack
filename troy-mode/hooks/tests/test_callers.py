"""Callers group (F05 design section 4, D40, and 13.1).

The hook sorts each call into the main session (no agent_id), a role
(agent_type matches the anchored role pattern), or another subagent (any
other agent_id). Each test pairs a refusal with a silent answer on the same
fixture, so a hook that refuses or allows everything fails.
"""

import unittest

from hook_helpers import (
    MAIN, OTHER_TYPES, ROLE_NAMES, HookTestCase, Project, bash_call, other, role, run_many,
    start_call, write_call,
)

# For each role: a path in its write scope and a path outside it.
ROLE_PATHS = {
    "architect": ("docs/adr/0001-storage.md", "src/pkg/app.py", "source"),
    "interface-designer": ("docs/features/F01/design.md", "docs/architecture.md", "docs"),
    "test-manager": ("docs/features/F01/test-plan.md", "docs/features/F01/design.md", "docs"),
    "developer": ("src/pkg/app.py", "tests/test_app.py", "tests"),
    "test-engineer": ("tests/test_app.py", "src/pkg/app.py", "source"),
    # The Code Reviewer's scope is empty; an ignored path is its silent case.
    "code-reviewer": ("reports/review.txt", "src/pkg/app.py", "source"),
}

# Subagents that are not roles: design section 4's examples, plus names a
# role pattern without ^ or $ would take for the Developer, a name without the
# plugin prefix, and an agent_id without agent_type.
NOT_ROLES = OTHER_TYPES + ("troy-developer", "troy-pstack:troy-developerx", None)


class CallerTests(HookTestCase):
    """Main session, roles, and other subagents get different limits."""

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts every role once."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, role(name)) for name in ROLE_NAMES])

    def test_main_session_files_are_not_limited(self):
        """The main session may write a test file, the config, and the rules: silent."""
        for rel in ("tests/test_app.py", ".troy-mode/config.toml", "docs/rules.md",
                    "src/pkg/app.py"):
            with self.subTest(path=rel):
                self.assert_silent(write_call(self.project, MAIN, self.project.path(rel)).run())

    def test_main_session_may_run_git_and_gh_writes(self):
        """The main session may commit, push, check out, reset, and comment on or merge a PR."""
        commands = ("git add -A && git commit -m 'Add counting'", "git push origin feature",
                    "git checkout -b topic", "git reset --hard HEAD",
                    "gh pr comment 7 --body 'Code Reviewer review, round 1: approved'",
                    "gh pr merge 7 --squash")
        for command in commands:
            with self.subTest(command=command):
                self.assert_silent(bash_call(self.project, MAIN, command).run())

    def test_the_same_git_and_gh_writes_are_refused_for_a_role(self):
        """Pair: the Developer's git commit, git push, and gh pr comment are refused."""
        dev = role("developer")
        cases = (("git add -A && git commit -m 'Add counting'", "git commit"),
                 ("git push origin feature", "git push"),
                 ("gh pr comment 7 --body 'Code Reviewer review, round 1: approved'",
                  "gh pr comment"))
        for command, fragment in cases:
            with self.subTest(command=command):
                self.assert_denied(bash_call(self.project, dev, command).run(), fragment)

    def test_each_role_is_recognized_by_its_scope(self):
        """Each of the six roles may write in its scope and is refused outside it."""
        calls, cases = [], []
        for name, (inside, outside, cls) in ROLE_PATHS.items():
            caller = role(name)
            calls += [write_call(self.project, caller, self.project.path(inside)),
                      write_call(self.project, caller, self.project.path(outside))]
            cases.append((name, inside, outside, cls))
        outs = run_many(calls)
        for index, (name, inside, outside, cls) in enumerate(cases):
            with self.subTest(role=name):
                self.assert_silent(outs[2 * index], f"{name} writing {inside}:")
                self.assert_denied(outs[2 * index + 1], outside, cls, "needs-answer",
                                   msg=f"{name} writing {outside}:")

    def test_other_subagents_may_change_nothing_in_the_repository(self):
        """Unknown troy-pstack names, general-purpose, Explore, and impostors: source refused."""
        calls = [write_call(self.project, other(t), self.project.path("src/pkg/app.py"))
                 for t in NOT_ROLES]
        for agent_type, out in zip(NOT_ROLES, run_many(calls)):
            with self.subTest(agent_type=agent_type):
                self.assert_denied(out, "src/pkg/app.py", "source", "needs-answer")

    def test_other_subagents_may_write_ignored_files(self):
        """Pair: the same subagents may write an ignored file (design section 4, Other subagent)."""
        calls = [write_call(self.project, other(t), self.project.path("reports/out.xml"))
                 for t in NOT_ROLES]
        for agent_type, out in zip(NOT_ROLES, run_many(calls)):
            with self.subTest(agent_type=agent_type):
                self.assert_silent(out)

    def test_other_subagents_get_read_only_git(self):
        """Other subagents may run git status and are refused git commit."""
        calls = []
        for agent_type in NOT_ROLES:
            calls += [bash_call(self.project, other(agent_type), "git status"),
                      bash_call(self.project, other(agent_type), "git commit -m x")]
        outs = run_many(calls)
        for index, agent_type in enumerate(NOT_ROLES):
            with self.subTest(agent_type=agent_type):
                self.assert_silent(outs[2 * index])
                self.assert_denied(outs[2 * index + 1], "git commit", "main session")

    def test_role_name_with_text_before_or_after_is_not_a_role(self):
        """A Developer or Test Engineer name with extra text gets no write scope.

        Planted bug caught: an unanchored role pattern (13.2). Without ^ and $,
        xtroy-pstack:troy-developer and troy-pstack:troy-developer-2 would be
        taken for the Developer and allowed to write source.
        """
        cases = (("troy-pstack:troy-developer", "src/pkg/app.py", "source"),
                 ("troy-pstack:troy-test-engineer", "tests/test_app.py", "tests"))
        impostors = {"troy-pstack:troy-developer": ("xtroy-pstack:troy-developer",
                                                    "troy-pstack:troy-developer-2",
                                                    "Xtroy-pstack:troy-developer",
                                                    "troy-pstack:troy-developer "),
                     "troy-pstack:troy-test-engineer": ("xtroy-pstack:troy-test-engineer",
                                                        "troy-pstack:troy-test-engineer-2",
                                                        "my-troy-pstack:troy-test-engineer")}
        for real, rel, cls in cases:
            real_caller = role(real.split(":troy-", 1)[1])
            with self.subTest(agent_type=real):
                self.assert_silent(write_call(self.project, real_caller,
                                              self.project.path(rel)).run())
            for name in impostors[real]:
                with self.subTest(agent_type=name):
                    out = write_call(self.project, other(name), self.project.path(rel)).run()
                    self.assert_denied(out, rel, cls, "needs-answer")


if __name__ == "__main__":
    unittest.main()
