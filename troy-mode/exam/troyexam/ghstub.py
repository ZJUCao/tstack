"""The gh stand-in on a run's PATH (design 4.2 step 4).

It answers `gh pr view`, `gh pr diff`, and `gh pr checks` from the local branch
and refuses everything else as a network error, so no command of a run reaches
GitHub. Its program text is written into the run's folder, where a role can
read it, so it holds no exam word and imports only the standard library.
"""

import json
from pathlib import Path

from .blinding import exam_words
from .errors import ExamError

OFFLINE = ("error connecting to api.github.com\n"
           "check your internet connection or https://githubstatus.com\n")

GH_PY = r'''"""gh for a local checkout: pull request reads come from the current branch."""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OFFLINE = ("error connecting to api.github.com\n"
           "check your internet connection or https://githubstatus.com\n")
FIELDS = ("number", "title", "body", "state", "url", "headRefName", "baseRefName",
          "headRefOid", "isDraft", "author", "files", "additions", "deletions",
          "changedFiles", "commits", "comments", "reviews", "labels", "statusCheckRollup",
          "mergeable")


def git(*args):
    """Runs git in the current folder and gives its output."""
    proc = subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.stdout


def offline():
    """Answers as gh does without a network."""
    sys.stderr.write(OFFLINE)
    return 1


def info():
    """The pull request of this branch."""
    return json.loads((HERE / "pr.json").read_text(encoding="utf-8"))


def numstat():
    """Each changed file with its added and deleted lines."""
    files = []
    for line in git("diff", "--numstat", "origin/main...HEAD").splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            add = int(parts[0]) if parts[0].isdigit() else 0
            rem = int(parts[1]) if parts[1].isdigit() else 0
            files.append({"path": parts[2], "additions": add, "deletions": rem})
    return files


def value(name, pr, branch):
    """One field of the pull request."""
    if name in ("files", "additions", "deletions", "changedFiles"):
        files = numstat()
        return {"files": files, "additions": sum(f["additions"] for f in files),
                "deletions": sum(f["deletions"] for f in files),
                "changedFiles": len(files)}[name]
    if name == "commits":
        rows = git("log", "--format=%H%x09%s", "origin/main..HEAD").splitlines()
        return [{"oid": r.split("\t", 1)[0], "messageHeadline": r.split("\t", 1)[-1]}
                for r in rows if r]
    simple = {"number": pr["number"], "title": pr["title"], "body": pr.get("body", ""),
              "state": "OPEN", "headRefName": branch, "baseRefName": "main",
              "url": f"https://github.com/{pr.get('repository', '')}/pull/{pr['number']}",
              "headRefOid": git("rev-parse", "HEAD").strip(), "isDraft": False,
              "author": {"login": pr.get("author", "")}, "comments": [], "reviews": [],
              "labels": [], "statusCheckRollup": [], "mergeable": "MERGEABLE"}
    return simple[name]


def jq(data, expr):
    """Applies the small part of jq that gh users need: .a, .a.b, .a[], .a[].b."""
    results = [data]
    for part in [p for p in expr.strip().split(".") if p] if expr.strip() != "." else []:
        many = part.endswith("[]")
        key = part[:-2] if many else part
        step = []
        for item in results:
            got = item.get(key) if key and isinstance(item, dict) else item
            if many and isinstance(got, list):
                step.extend(got)
            else:
                step.append(got)
        results = step
    return results


def view(args, pr, branch):
    """gh pr view."""
    fields, expr, i = None, None, 0
    while i < len(args):
        arg = args[i]
        if arg == "--json" and i + 1 < len(args):
            fields, i = args[i + 1], i + 2
            continue
        if arg.startswith("--json="):
            fields = arg.split("=", 1)[1]
        elif arg in ("--jq", "-q") and i + 1 < len(args):
            expr, i = args[i + 1], i + 2
            continue
        elif arg.startswith("--jq="):
            expr = arg.split("=", 1)[1]
        elif arg in ("--web", "-w"):
            return offline()
        i += 1
    if fields is None:
        sys.stdout.write(f"title:\t{pr['title']}\nstate:\tOPEN\nnumber:\t{pr['number']}\n"
                         f"url:\t{value('url', pr, branch)}\nbase:\tmain\nhead:\t{branch}\n--\n"
                         f"{pr.get('body', '')}\n")
        return 0
    names = [n.strip() for n in fields.split(",") if n.strip()]
    for name in names:
        if name not in FIELDS:
            sys.stderr.write(f'Unknown JSON field: "{name}"\n')
            return 1
    data = {name: value(name, pr, branch) for name in names}
    if expr is None:
        sys.stdout.write(json.dumps(data, indent=2) + "\n")
        return 0
    for item in jq(data, expr):
        sys.stdout.write((item if isinstance(item, str) else json.dumps(item)) + "\n")
    return 0


def main(argv):
    """Answers one gh command."""
    args, i = [], 0
    while i < len(argv):
        if argv[i] in ("-R", "--repo"):
            i += 2
            continue
        args.append(argv[i])
        i += 1
    if len(args) < 2 or args[0] != "pr" or args[1] not in ("view", "diff", "checks"):
        return offline()
    pr, branch = info(), git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if args[1] == "view":
        return view(args[2:], pr, branch)
    if args[1] == "diff":
        if "--web" in args or "-w" in args:
            return offline()
        extra = ["--name-only"] if "--name-only" in args else []
        sys.stdout.write(git("diff", *extra, "origin/main...HEAD"))
        return 0
    sys.stderr.write(f"no checks reported on the '{branch}' branch\n")
    return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
'''


def write_gh(bin_dir: Path, python: str, pr: dict) -> None:
    """Writes the stand-in into bin_dir: gh (for Git Bash), gh.cmd, gh.py, and pr.json.

    Args:
        bin_dir: The folder that comes first on the run's PATH.
        python: The Python that runs gh.py.
        pr: The pull request: number, title, body, and optionally repository and author.

    Raises:
        ExamError: A text it would write holds an exam word.
    """
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    program = bin_dir / "gh.py"
    texts = {
        "gh": f'#!/bin/sh\nexec "{Path(python).as_posix()}" -I "{program.as_posix()}" "$@"\n',
        "gh.cmd": f'@"{python}" -I "{program}" %*\r\n',
        "gh.py": GH_PY,
        "pr.json": json.dumps(pr, ensure_ascii=False, indent=1) + "\n",
    }
    for name, text in texts.items():
        hits = exam_words(text)
        if hits:
            raise ExamError(f"the gh stand-in's {name} would hold {', '.join(hits)}")
    for name, text in texts.items():
        with open(bin_dir / name, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    (bin_dir / "gh").chmod(0o755)
