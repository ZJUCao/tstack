"""Skills group (F05 design 7.4, F04 D36, and 13.1).

A subagent may call the Skill tool only for code-review and security-review,
with or without a plugin prefix, and never with --fix or --comment. The main
session may run any skill. Skill input fields are ``skill`` and ``args``
(contract section 1).
"""

import unittest

from hook_helpers import (
    CR, DEV, EXPLORE, GP, MAIN, HookTestCase, Project, run_many, skill_call, start_call,
)

ALLOWED = (
    ("code-review", None),
    ("code-review", ""),
    ("code-review", "high"),
    ("code-review", "high 42"),
    ("security-review", None),
    ("security-review", "medium"),
    ("troy-pstack:code-review", None),
    ("some-plugin:security-review", "low"),
    ("/code-review", "high"),
    ("/security-review", None),
)

REFUSED = (
    ("code-review", "--fix"),
    ("code-review", "high --fix"),
    ("code-review", "--comment"),
    ("code-review", "medium --comment 42"),
    ("security-review", "--fix"),
    ("troy-pstack:code-review", "--comment"),
    ("/code-review", "--fix"),
    ("simplify", None),
    ("update-config", None),
    ("code-review-extra", None),
    ("xcode-review", None),
    ("loop", "5m /code-review"),
    ("some-plugin:deploy", None),
)


def skill_name(skill):
    """Returns the skill's name without a leading slash or plugin prefix."""
    return skill.lstrip("/").split(":")[-1]


class SkillTests(HookTestCase):
    """Design 7.4 for roles, other subagents, and the main session."""

    @classmethod
    def setUpClass(cls):
        """Builds one project and starts the Code Reviewer and the Developer."""
        cls.project = Project()
        cls.addClassCleanup(cls.project.close)
        run_many([start_call(cls.project, c) for c in (CR, DEV)])

    def test_review_skills_pass_for_subagents(self):
        """code-review and security-review without --fix or --comment are silent."""
        cases = [(c, s, a) for c in (CR, DEV, GP, EXPLORE) for s, a in ALLOWED]
        outs = run_many([skill_call(self.project, c, s, a) for c, s, a in cases])
        for (caller, skill, args), out in zip(cases, outs):
            with self.subTest(caller=caller.label, skill=skill, args=args):
                self.assert_silent(out)

    def test_fix_comment_and_other_skills_are_refused_for_subagents(self):
        """--fix, --comment, and every other skill are refused with the skill name."""
        cases = [(c, s, a) for c in (CR, DEV, GP, EXPLORE) for s, a in REFUSED]
        outs = run_many([skill_call(self.project, c, s, a) for c, s, a in cases])
        for (caller, skill, args), out in zip(cases, outs):
            with self.subTest(caller=caller.label, skill=skill, args=args):
                self.assert_denied(out, skill_name(skill))

    def test_main_session_may_run_any_skill(self):
        """Pair: the same refused calls are silent for the main session."""
        outs = run_many([skill_call(self.project, MAIN, s, a) for s, a in REFUSED])
        for (skill, args), out in zip(REFUSED, outs):
            with self.subTest(skill=skill, args=args):
                self.assert_silent(out)


if __name__ == "__main__":
    unittest.main()
