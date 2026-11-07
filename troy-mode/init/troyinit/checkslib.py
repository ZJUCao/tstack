"""troy-check's own helpers, so troy-init reads patterns and headers exactly as it does.

troy-check sits next to the engine in troy-pstack, in troy-mode/checks/.
"""

import sys
from pathlib import Path

_CHECKS = Path(__file__).resolve().parents[2] / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

from troycheck.frontmatter import parse_header, version_key  # noqa: E402
from troycheck.globs import matches_any  # noqa: E402

__all__ = ["matches_any", "parse_header", "version_key"]
