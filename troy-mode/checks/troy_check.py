"""Entry point for troy-check, troy-mode's language-independent checks.

Usage:
    python troy_check.py pr --base <ref> --title <text> [options]
    python troy_check.py commit --message-file <path> [options]

See docs/troy-mode/design/F02-checks.md in tstack for the full design.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from troycheck.cli import main  # noqa: E402  (import after the path setup)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
