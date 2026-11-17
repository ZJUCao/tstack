"""Entry point of troy-mode's role exam (F16 design section 11).

Usage:
    python troy_exam.py affected --base <ref> [--head <ref>]
    python troy_exam.py run --base <ref> [--head <ref>] [--fixes <case>]... [--jobs <n>]
                            [--case <case>]... [--yes]
    python troy_exam.py prove <case>... [--ref <ref>] [--anchors]
    python troy_exam.py resume <exam ID>
    python troy_exam.py report <exam ID>
    python troy_exam.py block <exam ID>
    python troy_exam.py log <name> --id ... --hypothesis ... --change ... --before ... --after ...
                            --gate ... --verdict kept|reverted [--note ...]

Every command also takes --repo <tstack checkout>, --cases <folder>, and --json;
run, prove, affected, and resume take --env <prefix>. The work root is
D:\\Troy\\troy-mode-work unless TROY_EXAM_ROOT names another folder. The exam
runs on Troy's PC only, never in CI. See docs/troy-mode/design/F16-role-exam.md.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _folder in ("init", "checks", "hooks", "flow"):
    sys.path.insert(0, str(_HERE.parent / _folder))
sys.path.insert(0, str(_HERE))

from troyexam.cli import main  # noqa: E402  (import after the path setup)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
