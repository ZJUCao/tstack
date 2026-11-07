"""Entry point for troy-init's engine (F06 design section 3.2).

Usage:
    python troy_init.py setup --email <address> [options]
    python troy_init.py lang (python | cpp) [options]
    python troy_init.py upgrade [options]

The /troy-pstack:troy-init skill runs it, and F07 runs it directly. It changes
files and the repository's git config only; it never commits, pushes, or calls
GitHub. See docs/troy-mode/design/F06-troy-init.md in troy-pstack.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from troyinit.cli import main  # noqa: E402  (import after the path setup)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
