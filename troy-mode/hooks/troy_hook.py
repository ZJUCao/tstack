"""Entry point of troy-mode's Claude Code hooks (F05 design).

Usage:
    python troy_hook.py <Event>

<Event> is SessionStart, SubagentStart, PreToolUse, PostToolUse,
SubagentStop, or UserPromptExpansion. The hook input is JSON on stdin. See
docs/troy-mode/design/F05-hooks.md and F13-mode-guard.md in troy-pstack.

This file checks the Python version before it imports anything else, so it
must stay readable by old Pythons: no annotations and no f-strings here.
"""

import sys

if sys.version_info < (3, 11):
    import os

    sys.stderr.write("troy-mode hooks need Python 3.11 or newer; this is %s. "
                     "Set TROY_MODE_PYTHON.\n" % sys.version.split()[0])
    _project = os.environ.get("CLAUDE_PROJECT_DIR") or "."
    sys.exit(2 if os.path.isdir(os.path.join(_project, ".troy-mode")) else 0)

import os  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "checks"))
sys.path.insert(0, _HERE)

from troyhook.events import main  # noqa: E402  (import after the path setup)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
