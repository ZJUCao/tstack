"""role_inputs per case: the templates that a case's role would read from the plugin.

Written from F16 design 1.15, section 9.2 (F06 design D294), before the code changes.
``affected.role_inputs(case, plugin, project, env)`` keeps a plugin template
``troy-mode/templates/<rel>`` as a key of a case's inputs only when the case's project folder
has no file ``.troy-mode/templates/<rel>``, or the case's rendered brief names the template by
its path in the plugin, ``(plugin / "troy-mode/templates/<rel>").as_posix()``, as the rule
change brief does (F09). Roles fill templates from the project's copy (F04 common rule 7), so a
change to a template that a case's project holds does not affect that case. A brief that names
only the project's copy, ``.troy-mode/templates/<rel>``, does not count. The brief, the agent
file, and the skills stay as they were (F17 design D163).

Fixtures. A fake plugin folder holds the Architect's agent file, which names one skill,
``common.md``, that skill, and four templates: ``feature-design.md`` (CRLF), ``test-plan.md``,
``rules.md``, and ``issue/progress.md`` in a subfolder. Four projects: an empty one, one that
holds a copy of every template under ``.troy-mode/templates/``, one that holds some of them
(and copies of ``test-plan.md`` outside ``.troy-mode/templates/``), and one that holds every
template by its file name alone, without the subfolder. The copies' text differs from the
plugin's, so a value from the project's copy would show. ``affected.flow`` and
``affected.write_input`` are mocked, so no engine and no git runs: the fake ``flow`` gives each
case's brief from ``prompts``. One case's brief names nothing, one names ``rules.md`` by its
path in the plugin, one names only the project's copy of it, and one brief is refused.

On the current code (``d85172c``) every template under ``troy-mode/templates/`` is a key of
every case's inputs, whatever the project holds, so these tests fail there:
``test_a_template_the_project_holds_is_not_an_input``, ``test_per_file_not_per_folder``,
``test_a_subfolder_template_keeps_its_subfolder``,
``test_a_brief_that_names_the_template_in_the_plugin``,
``test_a_brief_that_names_only_the_projects_copy``,
``test_a_change_to_a_held_template_affects_nothing``, and
``test_a_change_to_a_template_that_only_the_projects_copy_names``. Three pass there by design,
as behavior the narrowing keeps: ``test_a_template_the_project_lacks_is_an_input``,
``test_a_change_to_a_template_the_project_lacks``, and
``test_a_change_to_a_template_that_the_brief_names``.

Planted bugs of F06 design 11.2 caught here:
"a template counted although the project holds it":
``test_a_template_the_project_holds_is_not_an_input``, ``test_per_file_not_per_folder``,
``test_a_subfolder_template_keeps_its_subfolder``,
``test_a_brief_that_names_only_the_projects_copy``, and
``test_a_change_to_a_held_template_affects_nothing``;
"a template the project lacks not counted":
``test_a_template_the_project_lacks_is_an_input``, ``test_per_file_not_per_folder``,
``test_a_subfolder_template_keeps_its_subfolder``, and
``test_a_change_to_a_template_the_project_lacks``;
"a template that the brief names not counted":
``test_a_brief_that_names_the_template_in_the_plugin`` and
``test_a_change_to_a_template_that_the_brief_names``.
"""

import unittest
from pathlib import Path
from unittest import mock

from exam_helpers import case_data, new_dir, write_case, write_file
from troyexam import affected
from troyexam.cases import load_case

TEMPLATES = "troy-mode/templates/"
FEATURE = "troy-mode/templates/feature-design.md"
TEST_PLAN = "troy-mode/templates/test-plan.md"
RULES = "troy-mode/templates/rules.md"
PROGRESS = "troy-mode/templates/issue/progress.md"
ALL_TEMPLATES = (FEATURE, TEST_PLAN, RULES, PROGRESS)
ARCHITECT = "agents/troy-architect.md"
COMMON = "troy-mode/roles/common.md"
SKILL = "skills/principle-alpha/SKILL.md"
PLUGIN_FILES = {
    ARCHITECT: "# Architect\n\nRead ${CLAUDE_PLUGIN_ROOT}/skills/principle-alpha/SKILL.md "
               "first.\n",
    COMMON: "# Common\n\nFill each template from the project's copy.\n",
    SKILL: "# Alpha\n",
    FEATURE: "# Design\r\n\r\nA template with CRLF.\r\n",
    TEST_PLAN: "# Test plan\n\nThe plugin's text.\n",
    RULES: "# Rules\n\nThe plugin's text.\n",
    PROGRESS: "# Progress\n\nThe plugin's text, in a subfolder.\n",
}
COPY = "# The project's copy\n"


def copy_path(template: str) -> str:
    """The project's copy of a plugin template: ``.troy-mode/templates/<rel>``."""
    return ".troy-mode/templates/" + template[len(TEMPLATES):]


# The projects: name mapped to the files they hold, each with COPY's text.
PROJECTS = {
    "empty": (),
    "full": tuple(copy_path(t) for t in ALL_TEMPLATES),
    # Holds feature-design.md and rules.md; test-plan.md only outside .troy-mode/templates/;
    # progress.md only without its subfolder.
    "partial": (copy_path(FEATURE), copy_path(RULES), "templates/test-plan.md",
                ".troy-mode/test-plan.md", ".troy-mode/templates/progress.md"),
    # Every template by its file name alone, so issue/progress.md is not held.
    "flat": (".troy-mode/templates/feature-design.md", ".troy-mode/templates/test-plan.md",
             ".troy-mode/templates/rules.md", ".troy-mode/templates/progress.md"),
}
# The cases: ID mapped to (role, task, item).
CASES = {
    "ar-plain": ("architect", "AR2", "F02"),
    "ar-plugin-rules": ("architect", "AR6", "F03"),
    "ar-copy-rules": ("architect", "AR6", "F04"),
    "ar-refused": ("architect", "AR2", "F09"),
}
REFUSED = ["F09 is not in the features table of docs/requirements.md on origin/main."]


def lf(text: str) -> str:
    """Text with CRLF read as LF, as role_inputs reads plugin files."""
    return text.replace("\r\n", "\n")


def prompts(plugin: Path) -> dict:
    """Each (task, item)'s rendered prompt.

    F03's names rules.md by its path in the plugin, as the rule change brief does; F04's names
    only the project's copy; F02's names no template.
    """
    rules = (plugin / RULES).as_posix()
    return {
        ("AR2", "F02"): "Task: AR2, review the interface design of F02.\nItem: F02\n"
                        "Read first:\n- docs/rules.md\nInput: None\n",
        ("AR6", "F03"): "Task: AR6, propose how to enforce the project rule.\nItem: F03\n"
                        f"Read first:\n- docs/rules.md\n- {rules}\nInput: None\n",
        ("AR6", "F04"): "Task: AR6, propose how to enforce the project rule.\nItem: F04\n"
                        "Read first:\n- docs/rules.md\n- .troy-mode/templates/rules.md\n"
                        "Input: None\n",
    }


def fake_flow(python, plugin, project, env, *args):
    """A stand-in for affected.flow: gives the brief report for the task and item in args."""
    key = (args[args.index("--task") + 1], args[args.index("--item") + 1])
    prompt = prompts(Path(plugin)).get(key)
    if prompt is None:
        return {"command": "brief", "ok": False, "notes": [], "problems": list(REFUSED)}
    return {"command": "brief", "ok": True, "notes": [], "problems": [], "prompt": prompt}


def make_plugin(changes: dict = None) -> Path:
    """The fake plugin folder with changes applied."""
    plugin = new_dir("tplplugin") / "tstack"
    for rel, content in {**PLUGIN_FILES, **(changes or {})}.items():
        write_file(plugin, rel, content)
    return plugin


def make_project(files) -> Path:
    """A project folder that holds the given files, each with COPY's text."""
    project = new_dir("tplproject")
    for rel in files:
        write_file(project, rel, COPY)
    return project


def make_cases() -> dict:
    """Each case of CASES, loaded from its own case folder."""
    root = new_dir("tplcases")
    found = {}
    for case_id, (role, task, item) in CASES.items():
        folder = write_case(root / case_id, case_data(case_id, role=role, task=task, item=item))
        found[case_id] = load_case(folder)
    return found


def inputs_of(case, plugin: Path, project: Path) -> dict:
    """role_inputs of one case with one plugin and project, flow and write_input mocked."""
    with mock.patch.object(affected, "flow", fake_flow), \
            mock.patch.object(affected, "write_input", return_value=None):
        return affected.role_inputs(case, plugin, project, {})


def template_keys(inputs: dict) -> set:
    """The keys of a case's inputs under troy-mode/templates/."""
    return {key for key in inputs if key.startswith(TEMPLATES)}


class TemplateInputsTests(unittest.TestCase):
    """affected.role_inputs keeps the templates a role would read from the plugin (9.2)."""

    @classmethod
    def setUpClass(cls):
        """The cases, the plugin, and one folder for each project of PROJECTS."""
        cls.cases = make_cases()
        cls.plugin = make_plugin()
        cls.projects = {name: make_project(files) for name, files in PROJECTS.items()}

    def inputs(self, case_id: str, project: str, plugin: Path = None) -> dict:
        """role_inputs of a case with a project of PROJECTS and the plugin (or another)."""
        return inputs_of(self.cases[case_id], plugin or self.plugin, self.projects[project])

    def test_a_template_the_project_lacks_is_an_input(self):
        """With the empty project, every template is a key of every case, its text the plugin's
        with CRLF read as LF (unchanged)."""
        for case_id in CASES:
            with self.subTest(case=case_id):
                inputs = self.inputs(case_id, "empty")
                self.assertEqual(template_keys(inputs), set(ALL_TEMPLATES))
                for template in ALL_TEMPLATES:
                    self.assertEqual(inputs[template], lf(PLUGIN_FILES[template]), template)

    def test_a_template_the_project_holds_is_not_an_input(self):
        """With the project that holds every template, no template is a key of a case whose
        brief names none, the refused one too; the same plugin with the empty project gives
        feature-design.md. The brief, the agent file, and the skill stay."""
        for case_id in ("ar-plain", "ar-refused"):
            with self.subTest(case=case_id):
                held = self.inputs(case_id, "full")
                self.assertEqual(set(held), {"brief", "agent", SKILL})
                self.assertEqual(held["agent"], PLUGIN_FILES[ARCHITECT])
                self.assertEqual(held[SKILL], PLUGIN_FILES[SKILL])
                self.assertIn(FEATURE, self.inputs(case_id, "empty"))
        self.assertEqual(self.inputs("ar-plain", "full")["brief"],
                         prompts(self.plugin)[("AR2", "F02")])
        self.assertEqual(self.inputs("ar-refused", "full")["brief"], f"problems: {REFUSED}")

    def test_per_file_not_per_folder(self):
        """The project that holds feature-design.md and rules.md, and test-plan.md only outside
        .troy-mode/templates/: test-plan.md and issue/progress.md are keys, with the plugin's
        text, and the held two are not."""
        inputs = self.inputs("ar-plain", "partial")
        self.assertEqual(template_keys(inputs), {TEST_PLAN, PROGRESS})
        self.assertEqual(inputs[TEST_PLAN], PLUGIN_FILES[TEST_PLAN])
        self.assertEqual(inputs[PROGRESS], PLUGIN_FILES[PROGRESS])

    def test_a_subfolder_template_keeps_its_subfolder(self):
        """issue/progress.md is held only by .troy-mode/templates/issue/progress.md: with the
        project that holds each template by its file name alone it is the one key, and with
        the project that holds every template it is not a key."""
        flat = self.inputs("ar-plain", "flat")
        self.assertEqual(template_keys(flat), {PROGRESS})
        self.assertEqual(flat[PROGRESS], PLUGIN_FILES[PROGRESS])
        self.assertNotIn(PROGRESS, self.inputs("ar-plain", "full"))

    def test_a_brief_that_names_the_template_in_the_plugin(self):
        """ar-plugin-rules' brief names rules.md by its path in the plugin: with the project
        that holds every template, rules.md is a key, with the plugin's text, and the other
        templates are not."""
        inputs = self.inputs("ar-plugin-rules", "full")
        self.assertIn((self.plugin / RULES).as_posix(), inputs["brief"])
        self.assertEqual(template_keys(inputs), {RULES})
        self.assertEqual(inputs[RULES], PLUGIN_FILES[RULES])
        self.assertEqual(template_keys(self.inputs("ar-plugin-rules", "partial")),
                         {RULES, TEST_PLAN, PROGRESS})

    def test_a_brief_that_names_only_the_projects_copy(self):
        """ar-copy-rules' brief names .troy-mode/templates/rules.md and not the plugin's path:
        with the project that holds every template, no template is a key."""
        inputs = self.inputs("ar-copy-rules", "full")
        self.assertIn(".troy-mode/templates/rules.md", inputs["brief"])
        self.assertEqual(template_keys(inputs), set())
        self.assertEqual(template_keys(self.inputs("ar-copy-rules", "partial")),
                         {TEST_PLAN, PROGRESS})

    def test_a_change_to_a_held_template_affects_nothing(self):
        """A plugin copy whose feature-design.md and rules.md changed, both held by the partial
        project: ar-plain's inputs are equal with the base and the head."""
        head = make_plugin({FEATURE: "# Design, changed\r\n", RULES: "# Rules, changed\n"})
        for project in ("partial", "full"):
            with self.subTest(project=project):
                self.assertEqual(self.inputs("ar-plain", project),
                                 self.inputs("ar-plain", project, head))

    def test_a_change_to_a_template_the_project_lacks(self):
        """A plugin copy whose test-plan.md, or issue/progress.md, changed, which the partial
        project lacks: ar-plain's inputs differ in that key alone (unchanged)."""
        base = self.inputs("ar-plain", "partial")
        for template in (TEST_PLAN, PROGRESS):
            with self.subTest(template=template):
                head = self.inputs("ar-plain", "partial",
                                   make_plugin({template: "# Changed\n"}))
                self.assertEqual(base.keys(), head.keys())
                differ = [key for key in base if base[key] != head[key]]
                self.assertEqual(differ, [template])
                self.assertEqual(head[template], "# Changed\n")

    def test_a_change_to_a_template_that_the_brief_names(self):
        """A plugin copy whose rules.md changed, held by the full project: ar-plugin-rules'
        inputs differ in rules.md, apart from the brief, which names each copy's own path."""
        base = self.inputs("ar-plugin-rules", "full")
        head = self.inputs("ar-plugin-rules", "full", make_plugin({RULES: "# Rules, changed\n"}))
        self.assertEqual(base.keys(), head.keys())
        differ = [key for key in base if key != "brief" and base[key] != head[key]]
        self.assertEqual(differ, [RULES])

    def test_a_change_to_a_template_that_only_the_projects_copy_names(self):
        """The same change with ar-copy-rules, whose brief names only the project's copy:
        its inputs are equal with the base and the head."""
        head = make_plugin({RULES: "# Rules, changed\n"})
        self.assertEqual(self.inputs("ar-copy-rules", "full"),
                         self.inputs("ar-copy-rules", "full", head))


if __name__ == "__main__":
    unittest.main()
