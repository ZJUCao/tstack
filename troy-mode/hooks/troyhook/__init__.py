"""troyhook: troy-mode's Claude Code hooks (F05 design).

The package keeps each troy-mode role inside its write scope, keeps every
other subagent read-only, limits subagents to read-only git and GitHub
commands, guards R19 and R21, lets roles read the plugin's own files, and
refuses poteto-mode's commands in a troy-mode project (F13 design). It
uses only the standard library and troy-check's modules, so it runs on any
Python 3.11 or newer without an environment.
"""
