"""role_inputs per case: the skills that a case's role reads, and no other (F17 design 5, 10).

Written from F17 design 1.0 and the step 1 contract (section 3) before the code exists.
``affected.role_inputs(case, plugin, project, env)`` compares, for each case, the brief, the
role's agent file, the templates, and only the skill folders that ``skills_in`` finds in the
case's agent file, ``common.md``, and the rendered brief's prompt; no longer every skill that
any role names. So a change to a skill that one role reads affects only that role's cases.

Fixtures. A fake plugin folder holds agent files for two roles (the Architect names
``principle-alpha`` and the entry skill, the Test Manager names ``principle-beta``),
``common.md`` (``principle-common``), one template, ``principle-card``, which only a rendered
brief names, ``unnamed``, which nothing names, and a ``brief.py`` that names
``principle-module`` in its source. ``affected.flow`` and ``affected.write_input`` are mocked,
so no engine and no git runs: the fake ``flow`` gives each case's brief from ``PROMPTS``, and
one case's brief is refused.

On ``origin/main`` (``ed51f81``) the four tests of the per-case rule fail, since every case
gets every named skill and none named only by its brief. Four pass there by design, as
behavior the contract keeps: the brief and agent keys
(``test_the_brief_and_agent_keys_stay``), the templates
(``test_templates_are_always_inputs``), common.md's skill
(``test_common_md_skills_are_every_cases``), and the skills that no input names
(``test_unnamed_skills_are_left_out``).

Planted bug of F17 design 12.2 (PR 1) caught here: "``affected`` comparing every case's skills
again": ``test_an_agent_files_skill_goes_to_its_role_only``,
``test_the_inputs_of_an_architect_case``, and
``test_a_change_to_one_roles_skill_affects_only_its_cases``.
"""

import unittest
from pathlib import Path
from unittest import mock

from exam_helpers import case_data, new_dir, write_case, write_file
from troyexam import affected
from troyexam.cases import load_case

FLOW_BRIEF = "troy-mode/flow/troyflow/brief.py"
TEMPLATE = "troy-mode/templates/feature-design.md"
ARCHITECT = "agents/troy-architect.md"
TEST_MANAGER = "agents/troy-test-manager.md"
COMMON = "troy-mode/roles/common.md"
PLUGIN_FILES = {
    ARCHITECT: "# Architect\n\nRead ${CLAUDE_PLUGIN_ROOT}/skills/principle-alpha/SKILL.md "
               "first. The entry skill is skills/troy-mode/SKILL.md.\n",
    TEST_MANAGER: "# Test Manager\n\nUse skills/principle-beta/ for the checklist.\n",
    COMMON: "# Common\n\nWrite by ${CLAUDE_PLUGIN_ROOT}/skills/principle-common/SKILL.md.\n",
    TEMPLATE: "# Design\r\n\r\nA template with CRLF.\r\n",
    FLOW_BRIEF: "CARD = 'skills/principle-module/SKILL.md'\n",
    "skills/principle-alpha/SKILL.md": "# Alpha\n",
    "skills/principle-alpha/reference/more.md": "# Alpha, more\n",
    "skills/principle-beta/SKILL.md": "# Beta\n",
    "skills/principle-common/SKILL.md": "# Common skill\n",
    "skills/principle-card/SKILL.md": "# Card\n",
    "skills/principle-module/SKILL.md": "# Module\n",
    "skills/unnamed/SKILL.md": "# Unnamed\n",
    "skills/troy-mode/SKILL.md": "# troy-mode\n",
}
ALPHA = ("skills/principle-alpha/SKILL.md", "skills/principle-alpha/reference/more.md")
BETA = ("skills/principle-beta/SKILL.md",)
COMMON_SKILL = ("skills/principle-common/SKILL.md",)
CARD = ("skills/principle-card/SKILL.md",)
LEFT_OUT = ("skills/principle-module/SKILL.md", "skills/unnamed/SKILL.md",
            "skills/troy-mode/SKILL.md", FLOW_BRIEF)
# The cases: ID mapped to (role, task, item).
CASES = {
    "ar-plain": ("architect", "AR2", "F02"),
    "ar-card": ("architect", "AR2", "F03"),
    "tm-plain": ("test-manager", "TM1", "F02"),
    "tm-refused": ("test-manager", "TM1", "F09"),
}
REFUSED = ["F09 is not in the features table of docs/requirements.md on origin/main."]


def prompts(plugin: Path) -> dict:
    """Each (task, item)'s rendered prompt; ar-card's names the card by its absolute path."""
    card = (plugin / CARD[0]).as_posix()
    return {
        ("AR2", "F02"): "Task: AR2, review the interface design of F02.\nItem: F02\n"
                        "Read first:\n- docs/rules.md\nInput: None\n",
        ("AR2", "F03"): "Task: AR2, review the interface design of F03. Apply `principle-card`: "
                        f"A line.\nItem: F03\nRead first:\n- docs/rules.md\n- {card}\n"
                        "Input: None\n",
        ("TM1", "F02"): "Task: TM1, write the test plan of F02.\nItem: F02\nRead first:\n"
                        "- docs/rules.md\nInput: None\n",
    }


def fake_flow(calls: list):
    """A stand-in for affected.flow: records each call and gives the case's brief report."""
    def flow(python, plugin, project, env, *args):
        """The report of ``brief`` for the task and item in args."""
        calls.append((Path(plugin), list(args)))
        key = (args[args.index("--task") + 1], args[args.index("--item") + 1])
        prompt = prompts(Path(plugin)).get(key)
        if prompt is None:
            return {"command": "brief", "ok": False, "notes": [], "problems": list(REFUSED)}
        return {"command": "brief", "ok": True, "notes": [], "problems": [], "prompt": prompt}
    return flow


def make_plugin(changes: dict = None) -> Path:
    """The fake plugin folder with changes applied."""
    plugin = new_dir("fakeplugin") / "tstack"
    for rel, content in {**PLUGIN_FILES, **(changes or {})}.items():
        write_file(plugin, rel, content)
    return plugin


def make_cases() -> dict:
    """Each case of CASES, loaded from its own case folder."""
    root = new_dir("affcases")
    found = {}
    for case_id, (role, task, item) in CASES.items():
        folder = write_case(root / case_id, case_data(case_id, role=role, task=task, item=item))
        found[case_id] = load_case(folder)
    return found


def inputs_of(cases: dict, plugin: Path, calls: list) -> dict:
    """role_inputs of every case with one plugin, flow and write_input mocked."""
    project = new_dir("affproject")
    with mock.patch.object(affected, "flow", fake_flow(calls)), \
            mock.patch.object(affected, "write_input", return_value=None):
        return {case_id: affected.role_inputs(case, plugin, project, {})
                for case_id, case in cases.items()}


class RoleInputsTests(unittest.TestCase):
    """affected.role_inputs, per case, with a fake plugin and no engine (contract 3)."""

    @classmethod
    def setUpClass(cls):
        """The inputs of every case with the plugin, and with a copy whose beta skill changed."""
        cls.cases = make_cases()
        cls.plugin = make_plugin()
        cls.calls = []
        cls.inputs = inputs_of(cls.cases, cls.plugin, cls.calls)
        cls.changed = inputs_of(cls.cases, make_plugin({BETA[0]: "# Beta, changed\n"}), [])

    def skill_keys(self, case_id: str) -> set:
        """The keys of a case's inputs under skills/."""
        return {key for key in self.inputs[case_id] if key.startswith("skills/")}

    def test_an_agent_files_skill_goes_to_its_role_only(self):
        """The Architect's cases get alpha's files and not beta's; the Test Manager's get
        beta's and not alpha's."""
        for case_id in ("ar-plain", "ar-card"):
            with self.subTest(case=case_id):
                self.assertLessEqual(set(ALPHA), self.skill_keys(case_id))
                self.assertFalse(set(BETA) & self.skill_keys(case_id), self.skill_keys(case_id))
        for case_id in ("tm-plain", "tm-refused"):
            with self.subTest(case=case_id):
                self.assertLessEqual(set(BETA), self.skill_keys(case_id))
                self.assertFalse(set(ALPHA) & self.skill_keys(case_id), self.skill_keys(case_id))

    def test_the_inputs_of_an_architect_case(self):
        """ar-plain's keys are exactly the brief, the agent file, the template, alpha's files,
        and common.md's skill."""
        self.assertEqual(set(self.inputs["ar-plain"]),
                         {"brief", "agent", TEMPLATE, *ALPHA, *COMMON_SKILL})

    def test_a_skill_named_only_in_the_brief(self):
        """ar-card's rendered brief names the card by its absolute path: its SKILL.md is an
        input, with its text; ar-plain's brief does not name it, so it is not."""
        self.assertIn(CARD[0], self.inputs["ar-card"])
        self.assertEqual(self.inputs["ar-card"][CARD[0]], PLUGIN_FILES[CARD[0]])
        self.assertNotIn(CARD[0], self.inputs["ar-plain"])
        self.assertNotIn(CARD[0], self.inputs["tm-plain"])

    def test_a_change_to_one_roles_skill_affects_only_its_cases(self):
        """A plugin whose beta skill changed: the Architect's inputs are the same, the Test
        Manager's differ in beta's SKILL.md alone."""
        for case_id in ("ar-plain", "ar-card"):
            with self.subTest(case=case_id):
                self.assertEqual(self.inputs[case_id].keys(), self.changed[case_id].keys())
                for key in self.inputs[case_id]:
                    if key != "brief":
                        self.assertEqual(self.inputs[case_id][key], self.changed[case_id][key],
                                         key)
        for case_id in ("tm-plain", "tm-refused"):
            with self.subTest(case=case_id):
                differ = [key for key in self.inputs[case_id]
                          if self.inputs[case_id][key] != self.changed[case_id].get(key)]
                self.assertEqual(differ, list(BETA))

    def test_common_md_skills_are_every_cases(self):
        """common.md's skill is an input of every case, the refused one too (unchanged)."""
        for case_id in CASES:
            with self.subTest(case=case_id):
                self.assertLessEqual(set(COMMON_SKILL), self.skill_keys(case_id))

    def test_templates_are_always_inputs(self):
        """The template is an input of every case, its CRLF read as LF (unchanged)."""
        for case_id in CASES:
            with self.subTest(case=case_id):
                self.assertEqual(self.inputs[case_id].get(TEMPLATE),
                                 "# Design\n\nA template with CRLF.\n")

    def test_the_brief_and_agent_keys_stay(self):
        """``brief`` is the rendered prompt, or ``problems: [...]`` for a refused brief, and
        ``agent`` the role's agent file; flow ran once per case with the plugin (unchanged)."""
        texts = prompts(self.plugin)
        self.assertEqual(self.inputs["ar-plain"]["brief"], texts[("AR2", "F02")])
        self.assertEqual(self.inputs["ar-card"]["brief"], texts[("AR2", "F03")])
        self.assertEqual(self.inputs["tm-refused"]["brief"], f"problems: {REFUSED}")
        for case_id, (role, _, _) in CASES.items():
            with self.subTest(case=case_id):
                self.assertEqual(self.inputs[case_id]["agent"],
                                 PLUGIN_FILES[f"agents/troy-{role}.md"])
        self.assertEqual(len(self.calls), len(CASES))
        for plugin, args in self.calls:
            self.assertEqual(plugin, self.plugin)
            self.assertEqual(args[0], "brief")

    def test_unnamed_skills_are_left_out(self):
        """The entry skill, a skill that nothing names, a skill that only a brief module's
        source names, and the module itself are no case's input (unchanged)."""
        for case_id in CASES:
            for key in LEFT_OUT:
                with self.subTest(case=case_id, key=key):
                    self.assertNotIn(key, self.inputs[case_id])


if __name__ == "__main__":
    unittest.main()
