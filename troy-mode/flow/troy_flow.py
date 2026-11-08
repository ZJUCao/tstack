"""Entry point of troy-mode's flow engine (F07 design section 3).

Usage:
    python troy_flow.py status [--write-progress] [--waiting <text>] [--note <text>]
    python troy_flow.py brief --task <task ID> --item <feature or bug ID> [--title <PR title>]
                              [--round <n>] [--input-file <path>]
    python troy_flow.py snapshot --role <role>
    python troy_flow.py check-run --run <run ID> [--allow-dependency <path>]...
    python troy_flow.py approve --doc <path> [--date <YYYY-MM-DD>]
    python troy_flow.py check-text --file <path>
    python troy_flow.py check-skips --report <troy-check JSON> --junit <path>...
    python troy_flow.py series

Every command also takes --repo <path> and --json. The troy-mode skill runs
the engine. It reads git, and GitHub through read-only gh calls, and writes
only the progress file, the header fields that approve changes, and its run
records. See docs/troy-mode/design/F07-entry-skill.md in troy-pstack.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _folder in ("init", "hooks", "checks"):
    sys.path.insert(0, str(_HERE.parent / _folder))
sys.path.insert(0, str(_HERE))

from troyflow.cli import main  # noqa: E402  (import after the path setup)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
