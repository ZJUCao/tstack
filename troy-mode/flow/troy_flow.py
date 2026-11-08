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
    python troy_flow.py release-test --version <vX.Y> --junit <path>...
    python troy_flow.py accept-version --tag <vX.Y.Z> --notes-file <path> [--date <YYYY-MM-DD>]
    python troy_flow.py release-notes --tag <vX.Y.Z> --out <path>
    python troy_flow.py retro --tag <vX.Y.Z>
    python troy_flow.py rule-id
    python troy_flow.py rule-row --id <P-ID> --rule-file <path> [--retire] [--date <YYYY-MM-DD>]

Every command also takes --repo <path> and --json. The troy-mode skill runs
the engine. It reads git, and GitHub through read-only gh calls, and writes
only the progress file, the header fields and change-log rows that approve
and accept-version change, release notes, the rules table rows that rule-row
writes, and its run records. See docs/troy-mode/design/F07-entry-skill.md,
F08-release.md, and F09-rule-change.md in troy-pstack.
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
