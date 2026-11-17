"""CI check: a PR that changes role instructions carries the role exam's result (F16 design 9.4).

Usage:
    python troy-mode/dev/check_exam.py [--event <path>] [--repo <path>]

It reads the pull request event (--event, else $GITHUB_EVENT_PATH). When the
PR's head has the same instruction hash as its merge base with the PR's base,
no instruction file changed and the check passes. Otherwise the description
must hold a "Role exam" section, outside any code block, whose Instructions
line is the first 12 characters of the head's hash and whose Result is
"passed", "no case affected", or "failed, accepted by Troy ...". The check
cannot prove that the runs happened; the report on Troy's PC is their record.
Exit 0 passes, 1 fails, 2 when it cannot run.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "troy-mode" / "exam"))

from troyexam.errors import ExamError  # noqa: E402
from troyexam.instructions import GitTree, instruction_hash, short_hash  # noqa: E402

HEADING = "## Role exam"
_FENCE = re.compile(r"^\s*(```|~~~)")


def parse_section(body: str) -> dict | None:
    """Finds the "Role exam" section outside fenced code blocks.

    Returns:
        {"result": ..., "instructions": ...}, with None for a missing line, or
        None when there is no such section.
    """
    lines = (body or "").replace("\r\n", "\n").split("\n")
    fenced, found, section = False, False, {"result": None, "instructions": None}
    for line in lines:
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if found and re.match(r"^#{1,2}\s", line):
            break
        if line.strip() == HEADING:
            found = True
            continue
        if found:
            match = re.match(r"^\s*(Result|Instructions):\s*(.*?)\s*$", line)
            if match:
                key = match.group(1).lower()
                if section[key] is None:
                    section[key] = match.group(2)
    return section if found else None


def result_ok(text: str | None) -> bool:
    """Tells whether a Result lets the PR merge."""
    text = (text or "").strip()
    return text in ("passed", "no case affected") or text.startswith("failed, accepted by Troy")


def _git(repo: Path, *args: str) -> str:
    """Runs git; ExamError when it fails."""
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if proc.returncode:
        raise ExamError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def check(body: str, base_hash: str, head_hash: str) -> tuple[bool, str]:
    """Decides the check from the description and the two hashes."""
    if base_hash == head_hash:
        return True, "no file of the instruction set changed"
    section = parse_section(body)
    if section is None:
        return False, ("this PR changes the roles' instruction set, and its description has no "
                       "\"Role exam\" section; run the role exam and paste `troy_exam.py block`")
    if section["instructions"] != short_hash(head_hash):
        return False, (f"the Role exam section is for instructions {section['instructions']}, but "
                       f"the head's are {short_hash(head_hash)}: run the exam again")
    if not result_ok(section["result"]):
        return False, f"the Role exam's Result is {section['result']!r}, which does not let it merge"
    return True, f"the Role exam section matches the head's instructions {short_hash(head_hash)}"


def main(argv: list[str]) -> int:
    """Runs the check."""
    parser = argparse.ArgumentParser(prog="check_exam.py")
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    if not args.event:
        print("check_exam: no event; nothing to check")
        return 0
    try:
        event = json.loads(Path(args.event).read_text(encoding="utf-8"))
        pr = event.get("pull_request")
        if not pr:
            print("check_exam: not a pull request; nothing to check")
            return 0
        repo = Path(args.repo)
        base, head = pr["base"]["sha"], pr["head"]["sha"]
        merge_base = _git(repo, "merge-base", base, head)
        ok, message = check(pr.get("body") or "", instruction_hash(GitTree(repo, merge_base)),
                            instruction_hash(GitTree(repo, head)))
    except (OSError, ValueError, KeyError, ExamError) as exc:
        print(f"check_exam: error: {exc}", file=sys.stderr)
        return 2
    print(f"check_exam: {'pass' if ok else 'fail'}: {message}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
