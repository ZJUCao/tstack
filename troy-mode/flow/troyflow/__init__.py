"""troy-mode's flow engine (F07 design section 3): the state, briefs, run checks, and approvals."""

# The plugin's name as Claude Code puts it before the roles' agent names (F19 design 5.1).
# troyhook.scopes.PLUGIN_PREFIX says the same; a test keeps them equal.
PLUGIN_PREFIX = "tstack:"
