"""troy-mode's role exam (F16 design): cases, blind runs, the judge, and the comparison."""

# The plugin's folder name for each copy, and the prefix of the roles' agent names (F19 design).
PLUGIN_NAME = "tstack"
AGENT_PREFIX = "tstack:troy-"
# Turns the installed plugin off for one session only (design 11.3, F19 design D194).
INSTALLED_OFF = '{"enabledPlugins":{"tstack@tstack":false}}'
# The roles that run as subagents (design section 3, D151).
SUBAGENT_ROLES = ("architect", "interface-designer", "test-manager", "developer",
                  "test-engineer", "code-reviewer")
DEFAULT_ROOT = r"D:\Troy\troy-mode-work"
ROOT_VARIABLE = "TROY_EXAM_ROOT"
CLI_VARIABLE = "TROY_EXAM_CLI"
