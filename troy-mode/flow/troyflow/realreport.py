"""The evidence of a real run: the PR description's "Real run" section (F12 design 8).

The engine writes the section, so the Product Manager copies it rather than
retyping it. It names the program by its command and its environment, and
shows paths only after the path map, so it holds no folder of Troy's PC.
When it would pass 60,000 characters, the real output goes into PR comments.
"""

import json
from pathlib import Path

from . import repo as git
from .realcompare import NORMALIZATIONS

LIMIT = 60_000
COMMENT_HEADING = "Real run output, part {n}"
PIPES = "Through pipes, not a console (F12 design section 10)."
NOT_PROVEN = (
    "How Windows Terminal draws the text: the font, the width it gives each Chinese "
    "character, colors, and wrapping.",
    "What Python does in a real console, which it writes through the console's own text "
    "interface.",
    "The order of standard output and standard error on screen, when a command writes to "
    "both.",
    "How PowerShell itself splits a command line: quotes, empty arguments, and the "
    "differences between Windows PowerShell 5.1 and PowerShell 7.",
    "Commands that read keys or answers, or open an editor.",
    "Troy's own install: uv tool install, PATH, and the Python that uv manages.",
    "Words that depend on the day, such as this and next, where the run file replaced them.",
)


def _code(text: str) -> str:
    """A Markdown code span that survives backticks and table pipes."""
    text = text.replace("|", "\\|")
    return f"`` {text} ``" if "`" in text else f"`{text}`"


def _short(commit: str | None) -> str:
    """A commit's short ID."""
    return (commit or "unknown")[:7]


def _commands(report: dict) -> list[tuple[dict, dict, dict]]:
    """Every (prototype, section, command) of the report, in order."""
    return [(p, s, c) for p in report.get("prototypes", []) for s in p["sections"]
            for c in s["commands"]]


def _plural(count: int, one: str, many: str) -> str:
    """'1 command' or '3 commands'."""
    return f"{count} {one if count == 1 else many}"


def result_line(report: dict) -> str:
    """The counts in one line, such as "41 commands match. 3 wait for F12. None did not run."."""
    counts = (report.get("counts") or {}).get("all")
    if counts is None:
        return "The run did not start."
    parts = [f"{_plural(counts['matches'], 'command matches', 'commands match')}."]
    if counts["mismatch"]:
        parts.append(f"{_plural(counts['mismatch'], 'does', 'do')} not match.")
    waits = sorted({c["result"].split()[-1] for _, _, c in _commands(report)
                    if c["result"].startswith("waits for")})
    if counts["waits"]:
        parts.append(f"{counts['waits']} wait for {', '.join(waits)}.")
    parts.append(f"{counts['not_run']} did not run." if counts["not_run"] else
                 "None did not run.")
    return " ".join(parts)


def _header(report: dict) -> list[str]:
    """The header lines: commit, program, system, date, and the pipes line."""
    base = report.get("base")
    commit = f"`{_short(report.get('commit'))}`"
    if base and base != report.get("commit"):
        commit += f", on top of origin/main `{_short(base)}`"
    elif base:
        commit += " (origin/main)"
    program = report.get("program") or {}
    names = ", ".join(f"`{n}`" for n in program.get("names") or []) or "none"
    where = f", from the environment `{program['environment']}`" \
        if program.get("environment") else ""
    python = f", Python {program['python']}" if program.get("python") else ""
    return ["## Real run", "", f"- Commit: {commit}", f"- Program: {names}{where}{python}",
            f"- System: {report.get('system')}", f"- Date: {report.get('date')}", f"- {PIPES}"]


def _result(report: dict) -> list[str]:
    """The Result part."""
    lines = ["", "### Result", "", result_line(report)]
    if report.get("label"):
        lines += ["", f"Label: {report['label']}. {report.get('label_reason', '')}".rstrip()]
    problems = report.get("problems") or []
    if problems:
        lines += ["", "Problems:"] + [f"- {p['kind']}: {p['message']}" for p in problems]
    return lines


def _table(report: dict) -> list[str]:
    """The Commands part: one row per command."""
    lines = ["", "### Commands", ""]
    rows = _commands(report)
    if not rows:
        return lines + ["None."]
    lines += ["| Prototype | Section | Command | Exit | Result |",
              "| --- | --- | --- | --- | --- |"]
    for proto, section, command in rows:
        code = "" if command["exit"] is None else str(command["exit"])
        lines.append(f"| {Path(proto['file']).name} | {section['heading'].replace('|', '/')} | "
                     f"{_code(command['typed'])} | {code} | {command['result']} |")
    return lines


def _adaptations(report: dict) -> list[str]:
    """The Adaptations part: path map, replaced commands, starts, and normalizations."""
    lines = ["", "### Adaptations", "", "Path map:"]
    pairs = sorted({(p["prototype"], p["run"]) for proto in report.get("prototypes", [])
                    for p in proto.get("paths", [])})
    lines += [f"- {_code(a)} is {_code(b)}" for a, b in pairs] or ["- None."]
    lines += ["", "Replaced commands:"]
    replaced = [(Path(p["file"]).name, r) for p in report.get("prototypes", [])
                for r in p.get("replaced", [])]
    lines += [f"- {name}, {r['section']}: {_code(r['typed'])} ran as {_code(r['run'])}. "
              f"{r['reason']}" for name, r in replaced] or ["- None."]
    lines += ["", "How each section started:"]
    starts = [(Path(p["file"]).name, s) for p in report.get("prototypes", [])
              for s in p["sections"]]
    lines += [f"- {name}, {s['heading']}: {s.get('describe', s['start'])}"
              for name, s in starts] or ["- None."]
    lines += ["", "Normalizations:"] + [f"{n}. {text}" for n, text in
                                        enumerate(NORMALIZATIONS, start=1)]
    return lines


def _changes(changes: dict) -> list[str]:
    """The Changes part."""
    lines = ["", "### Changes", ""]
    protos = changes.get("prototypes") or []
    lines.append("Prototypes changed in this PR: " +
                 (", ".join(f"`{p}`" for p in protos) if protos else "None") + ".")
    run_files = changes.get("run_files")
    if run_files is None:
        lines.append("Run files changed after the first run: this is the first run.")
    else:
        lines.append("Run files changed after the first run: " +
                     (", ".join(f"`{p}`" for p in run_files) if run_files else "None") + ".")
    return lines


def _fence(lines: list[str]) -> str:
    """A backtick fence longer than any run of backticks in the lines."""
    most = max((len(part) for line in lines for part in _ticks(line)), default=0)
    return "`" * max(3, most + 1)


def _ticks(line: str) -> list[str]:
    """The runs of backticks in a line."""
    runs, current = [], ""
    for char in line:
        if char == "`":
            current += char
        elif current:
            runs.append(current)
            current = ""
    return runs + ([current] if current else [])


def _transcript(section: dict) -> list[str]:
    """A section's real output in the transcript's own form."""
    rows = [(e["line"] or 0, "env", e) for e in section.get("env", [])]
    rows += [(c["line"] if c["line"] is not None else 10 ** 9, "command", c)
             for c in section["commands"]]
    lines: list[str] = []
    for _, kind, entry in sorted(rows, key=lambda r: r[0]):
        if kind == "env":
            lines.append(f"PS> $env:{entry['name']} = \"{entry['value']}\"")
        elif entry["kind"] == "file":
            lines.append(f"# The program wrote {entry['typed'][len('file '):]}:")
            lines += entry["real"] if entry["real"] is not None else ["(not checked)"]
        elif entry["real"] is None:
            lines.append(f"PS> {entry['run']}")
            why = entry["result"] if entry["result"] != "not run" else \
                f"not run: {entry['reason']}"
            lines.append(f"({why})")
        else:
            lines.append(f"PS> {entry['run']}")
            lines += entry["real"]
            if entry["expected_exit"] is not None or entry["exit"] not in (0, None):
                lines += ["PS> $LASTEXITCODE", str(entry["exit"])]
    return lines


def _units(report: dict) -> list[tuple[str, str]]:
    """The real output as (prototype, Markdown) units, one per section."""
    units = []
    for proto in report.get("prototypes", []):
        for section in proto["sections"]:
            lines = _transcript(section)
            fence = _fence(lines)
            text = "\n".join([f"**{section['heading']}**", "", fence + "text"] + lines + [fence])
            units.append((proto["file"], text))
    return units


def _details(units: list[tuple[str, str]]) -> list[str]:
    """Folds units into one <details> block per prototype."""
    lines, current = [], None
    for file, text in units:
        if file != current:
            if current is not None:
                lines += ["", "</details>"]
            lines += ["", "<details>", f"<summary>{file}</summary>"]
            current = file
        lines += ["", text]
    if current is not None:
        lines += ["", "</details>"]
    return lines


def _split(units: list[tuple[str, str]]) -> list[str]:
    """Packs the real output into comments of at most LIMIT characters each."""
    pieces = []
    for file, text in units:
        while len(text) > LIMIT - 1000:
            cut = text.rfind("\n", 0, LIMIT - 2000)
            head, text = text[:cut], text[cut + 1:]
            fence = _fence(head.split("\n"))
            pieces.append((file, head + "\n" + fence))
            text = f"{fence}text\n{text}"
        pieces.append((file, text))
    comments, current = [], []
    for piece in pieces:
        trial = current + [piece]
        if current and len(_comment(len(comments) + 1, trial)) > LIMIT:
            comments.append(_comment(len(comments) + 1, current))
            current = [piece]
        else:
            current = trial
    if current:
        comments.append(_comment(len(comments) + 1, current))
    return comments


def _comment(number: int, pieces: list[tuple[str, str]]) -> str:
    """One comment of real output."""
    return "\n".join([COMMENT_HEADING.format(n=number)] + _details(pieces)) + "\n"


def description(report: dict, changes: dict) -> tuple[str, list[str]]:
    """Writes the "Real run" section and, when it is too long, the comments (design 8).

    Returns:
        The section's text, and the comments that hold the real output (or none).
    """
    head = _header(report) + _result(report) + _table(report) + _adaptations(report)
    head += _changes(changes)
    head += ["", "### Points at later features", "", "None."]
    head += ["", "### Not proven", ""] + [f"- {text}" for text in NOT_PROVEN]
    units = _units(report)
    whole = "\n".join(head + ["", "### Real output"] + (_details(units) or ["", "None."])) + "\n"
    if len(whole) <= LIMIT:
        return whole, []
    comments = _split(units)
    names = f"{len(comments)} comments" if len(comments) > 1 else "one comment"
    note = (f"The real output is longer than a PR description allows, so it is in {names} "
            f"after this description, headed \"{COMMENT_HEADING.format(n=1)}\" and on.")
    return "\n".join(head + ["", "### Real output", "", note]) + "\n", comments


def changes(repo, report: dict) -> dict:
    """What changed in this PR: the prototypes, and the run files since the first run."""
    files = [p["file"] for p in report.get("prototypes", [])]
    protos = []
    base = report.get("base")
    if base and files and base != report.get("commit"):
        out = git.git(repo, "diff", "--name-only", base, "HEAD", "--", *files)
        protos = sorted(line.strip() for line in out.splitlines() if line.strip())
    earlier = _first_run_files(repo.state_dir() / "flow", report.get("item") or "all")
    if earlier is None:
        return {"prototypes": protos, "run_files": None}
    now = report.get("run_files") or {}
    return {"prototypes": protos,
            "run_files": sorted(p for p, sha in now.items() if p in earlier and earlier[p] != sha)}


def _first_run_files(folder: Path, item: str) -> dict | None:
    """Each run file as the first earlier run that had it saw it, or None without an earlier run.

    A run file that no earlier run had is new in this PR, not changed after
    the first run: the Product Manager runs once before writing run files.
    """
    numbered = []
    for path in folder.glob(f"real-run-{item}-*.json"):
        tail = path.stem.rsplit("-", 1)[-1]
        if tail.isdigit():
            numbered.append((int(tail), path))
    if not numbered:
        return None
    first: dict = {}
    for _, path in sorted(numbered):
        try:
            seen = json.loads(path.read_text(encoding="utf-8")).get("run_files") or {}
        except (OSError, ValueError):
            continue
        for name, sha in seen.items():
            first.setdefault(name, sha)
    return first


def markdown(report: dict) -> str:
    """The report for a person and for TM8's Input: the description, the mismatches, problems."""
    parts = [report["description"].rstrip()]
    parts += [comment.rstrip() for comment in report.get("comments", [])]
    mismatches = [(p, s, c) for p, s, c in _commands(report) if c["result"] == "mismatch"]
    lines = ["## Mismatches", ""]
    if not mismatches:
        lines.append("None.")
    for proto, section, command in mismatches:
        lines += [f"### {proto['file']}, {section['heading']}: {command['typed']}", "",
                  f"- Run as: `{command['run']}`", f"- Exit code: {command['exit']}"
                  + (f", the prototype shows {command['expected_exit']}"
                     if command["expected_exit"] is not None else ""),
                  f"- Why: {command['reason']}", "", "```diff", command["diff"].rstrip(), "```",
                  ""]
    lines += ["", "## Problems", ""]
    lines += [f"- {p['kind']}: {p['message']}" for p in report.get("problems", [])] or ["None."]
    bugs = report.get("open_bugs")
    lines += ["", "## Open bugs of earlier real runs", ""]
    lines += [f"- #{b['number']} {b['title']}" for b in bugs or []] or \
        ["None." if bugs is not None else "Not read: see the notes."]
    return "\n\n".join(parts) + "\n\n" + "\n".join(lines) + "\n"
