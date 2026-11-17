"""The plugin's name in every place that holds it (F19 design 4.1, 4.3, 5, and 11.1).

F19 renames the plugin to tstack. Its name is written in plugin.json, in
marketplace.json, in hooks.json's matchers and Read rule, in one constant of
the hooks (troyhook.scopes.PLUGIN_PREFIX) and one of the engine
(troyflow.PLUGIN_PREFIX), in the dev environment, and in the CI workflows.
These tests check that each says tstack and that they agree with plugin.json.

F19 planted bugs (design 11.3) caught here: plugin.json's or marketplace.json's
name left (PluginJsonTests, MarketplaceTests, and the agreement tests);
one SubagentStart or SubagentStop matcher left and the if rule left
(HooksJsonTests); environment.yml's name left (WorkflowAndEnvironmentTests).
"""

import importlib
import json
import re
import sys
import unittest
from pathlib import Path

from pack_helpers import REPO, TROY_MODE, WORKFLOWS, step_blocks, steps

PLUGIN_JSON = REPO / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO / ".claude-plugin" / "marketplace.json"
HOOKS_JSON = REPO / "hooks" / "hooks.json"
ENVIRONMENT = TROY_MODE / "dev" / "environment.yml"
DOCS_WORKFLOW = WORKFLOWS / "troy-docs.yml"
SAMPLE_WORKFLOWS = (WORKFLOWS / "troy-python-sample.yml", WORKFLOWS / "troy-cpp-sample.yml")
NAME = "tstack"
OLD = "troy" + "-pstack"  # the plugin's name before tstack (F19 design 4.1)
OLD_NAME = re.compile(r"troy[-_ ]?pstack", re.IGNORECASE)

# F19 design 4.3: plugin.json's description and the plugin's entry in marketplace.json.
CREDIT = ("tstack, Troy's own stack for Claude Code. Most of its skills, principles, playbooks, "
          "and subagent workflows come from Lauren Tan's pstack 0.15.36, used under its MIT "
          "license. troy-mode, the workflow from requirements to released versions, is Troy's "
          "own work. Not affiliated with or endorsed by Lauren Tan or Cursor.")
MARKETPLACE_DESCRIPTION = "Troy's personal Claude Code plugins. Currently one: tstack."
# F13 design D122: the mode guard's matcher, which F19 leaves unchanged (design 5.2).
GUARD_MATCHER = "^([^:]+:)?(poteto-mode|no-comments)$"


def load_json(path: Path) -> dict:
    """Reads a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def plugin_name() -> str:
    """The name in plugin.json."""
    return load_json(PLUGIN_JSON)["name"]


def package_module(folder: Path, name: str):
    """Imports a module of troy-mode's hooks or engine, with its folder on sys.path.

    troy-mode/checks goes on sys.path too, as troy_hook.py sets it.
    """
    for path in (folder, TROY_MODE / "checks"):
        if str(path) not in sys.path:
            sys.path.append(str(path))
    return importlib.import_module(name)


def hook_groups(event: str) -> list:
    """The groups of one event in hooks.json."""
    return load_json(HOOKS_JSON)["hooks"].get(event, [])


def old_name_lines(path: Path) -> list:
    """The lines of a file that name the plugin before tstack, in any spelling."""
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if OLD_NAME.search(line)]


class PluginJsonTests(unittest.TestCase):
    """.claude-plugin/plugin.json (design 4.1, 4.3, and 5.5)."""

    @classmethod
    def setUpClass(cls):
        """Reads plugin.json once."""
        cls.data = load_json(PLUGIN_JSON)

    def test_name_is_tstack(self):
        """The plugin is named tstack, so its commands are /tstack:<skill>."""
        self.assertEqual(NAME, self.data["name"])

    def test_keywords_name_tstack_and_keep_pstack_fork(self):
        """The keyword tstack replaces the old name, and pstack-fork stays."""
        keywords = self.data["keywords"]
        self.assertIn(NAME, keywords)
        self.assertNotIn(OLD, keywords)
        self.assertIn("pstack-fork", keywords)
        self.assertEqual([], [word for word in keywords if OLD_NAME.search(word)])

    def test_description_is_the_credit_of_design_4_3(self):
        """The description credits Lauren Tan's pstack and says troy-mode is Troy's own work."""
        self.assertEqual(CREDIT, self.data["description"])

    def test_version_is_0_6_0_or_a_later_minor_version(self):
        """F19 raises the minor version: 0.6.0, or the next free 0.x.0 (D193)."""
        match = re.fullmatch(r"0\.(\d+)\.0", self.data["version"])
        self.assertIsNotNone(match, self.data["version"])
        self.assertGreaterEqual(int(match.group(1)), 6, self.data["version"])


class MarketplaceTests(unittest.TestCase):
    """.claude-plugin/marketplace.json (design 4.1 and 4.3, D193)."""

    @classmethod
    def setUpClass(cls):
        """Reads marketplace.json once."""
        cls.data = load_json(MARKETPLACE_JSON)

    def test_marketplace_is_named_tstack(self):
        """The marketplace is tstack, so the install ID is tstack@tstack."""
        self.assertEqual(NAME, self.data["name"])

    def test_marketplace_description(self):
        """The marketplace's description names its one plugin, tstack."""
        self.assertEqual(MARKETPLACE_DESCRIPTION, self.data["description"])

    def test_one_plugin_entry_named_as_plugin_json_with_the_credit(self):
        """The one plugin entry is named tstack, as plugin.json, and carries the credit."""
        plugins = self.data["plugins"]
        self.assertEqual(1, len(plugins), plugins)
        self.assertEqual(NAME, plugins[0]["name"])
        self.assertEqual(plugin_name(), plugins[0]["name"])
        self.assertEqual(CREDIT, plugins[0]["description"])


class HooksJsonTests(unittest.TestCase):
    """hooks/hooks.json names the plugin as plugin.json does (design 5.2)."""

    def one_group(self, event: str) -> dict:
        """The one group of an event, failing if there is not exactly one."""
        groups = hook_groups(event)
        self.assertEqual(1, len(groups), f"{event}: {groups}")
        return groups[0]

    def test_subagent_matchers_name_the_plugin(self):
        """SubagentStart and SubagentStop match ^tstack:troy-, plugin.json's name and :troy-."""
        for event in ("SubagentStart", "SubagentStop"):
            with self.subTest(event=event):
                matcher = self.one_group(event).get("matcher")
                self.assertEqual("^tstack:troy-", matcher)
                self.assertEqual(f"^{plugin_name()}:troy-", matcher)

    def test_read_if_rule_names_the_plugin_folder(self):
        """The PreToolUse Read entry's if rule is Read(//**/tstack/**)."""
        reads = [group for group in hook_groups("PreToolUse") if group.get("matcher") == "Read"]
        self.assertEqual(1, len(reads), reads)
        rules = [hook.get("if") for hook in reads[0]["hooks"]]
        self.assertEqual(["Read(//**/tstack/**)"], rules)
        self.assertEqual([f"Read(//**/{plugin_name()}/**)"], rules)

    def test_user_prompt_expansion_matcher_is_unchanged(self):
        """The mode guard's matcher takes any prefix, so F19 leaves it as it was."""
        self.assertEqual(GUARD_MATCHER, self.one_group("UserPromptExpansion").get("matcher"))


class PrefixConstantTests(unittest.TestCase):
    """The one constant in each package (design 5.1) agrees with plugin.json."""

    def test_hooks_prefix_is_the_plugin_name_and_a_colon(self):
        """troyhook.scopes.PLUGIN_PREFIX is "tstack:", plugin.json's name followed by ":"."""
        prefix = package_module(TROY_MODE / "hooks", "troyhook.scopes").PLUGIN_PREFIX
        self.assertEqual("tstack:", prefix)
        self.assertEqual(plugin_name() + ":", prefix)

    def test_engine_prefix_is_the_plugin_name_and_a_colon(self):
        """troyflow.PLUGIN_PREFIX is "tstack:", plugin.json's name followed by ":"."""
        prefix = package_module(TROY_MODE / "flow", "troyflow").PLUGIN_PREFIX
        self.assertEqual("tstack:", prefix)
        self.assertEqual(plugin_name() + ":", prefix)


class WorkflowAndEnvironmentTests(unittest.TestCase):
    """The dev environment and CI (design 5.4 and 6.4, D196)."""

    def test_environment_is_named_tstack(self):
        """troy-mode/dev/environment.yml creates the env tstack and names no old plugin."""
        names = re.findall(r"^name:\s*(\S+)\s*$",
                           ENVIRONMENT.read_text(encoding="utf-8"), re.MULTILINE)
        self.assertEqual([NAME], names)
        self.assertEqual([], old_name_lines(ENVIRONMENT))

    def test_docs_workflow_runs_the_name_check(self):
        """troy-docs.yml has a step that runs troy-mode/dev/check_name.py."""
        runs = [run for _, run in steps(DOCS_WORKFLOW)]
        self.assertTrue(any(re.fullmatch(r"python3? troy-mode/dev/check_name\.py", run)
                            for run in runs), runs)

    def test_docs_workflow_runs_on_every_pull_request(self):
        """troy-docs.yml's pull_request trigger has no paths filter (design 5.4)."""
        lines = DOCS_WORKFLOW.read_text(encoding="utf-8").splitlines()
        start = next(i for i, line in enumerate(lines) if re.match(r"^on:\s*$", line))
        block = []
        for line in lines[start + 1:]:
            if line.strip() and not line.startswith((" ", "#")):
                break
            block.append(line)
        self.assertTrue(any(re.match(r"^\s+pull_request:", line) for line in block), block)
        self.assertEqual([], [line for line in block
                              if re.match(r"^\s+(paths|paths-ignore):", line)])

    def test_sample_workflows_check_the_plugin_out_into_tstack(self):
        """Both sample workflows check the plugin out into tstack/ and run its build_sample.py."""
        for path in SAMPLE_WORKFLOWS:
            with self.subTest(workflow=path.name):
                checkouts = [block for block in step_blocks(path)
                             if block.get("uses", "").startswith("actions/checkout@")]
                self.assertTrue(checkouts, f"{path.name} checks nothing out")
                paths = [re.findall(r"^\s+path:\s*(\S+)\s*$", block["text"], re.MULTILINE)
                         for block in checkouts]
                self.assertIn([NAME], paths, paths)
                runs = [run for _, run in steps(path) if "build_sample.py" in run]
                build = "python3 tstack/troy-mode/dev/build_sample.py build "
                self.assertTrue(any(run.startswith(build) for run in runs), runs)
                calls = re.findall(r"(\S*)troy-mode/dev/build_sample\.py", "\n".join(runs))
                self.assertEqual([], [call for call in calls
                                      if call not in ("tstack/", "../tstack/")], calls)
                self.assertEqual([], old_name_lines(path))


if __name__ == "__main__":
    unittest.main()
