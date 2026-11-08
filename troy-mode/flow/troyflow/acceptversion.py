"""accept-version and release-notes: Troy's acceptance and the tag's notes (F08 design 5.7).

accept-version records Troy's acceptance of a version in its test plan and the
plan's mirror: a row in the acceptance record, the next major version, the
status, and a change-log row. release-notes writes the tag's section of
CHANGELOG.md on origin/main for the GitHub release.
"""

from pathlib import Path

from . import repo as git
from .approve import check_date, header_of, next_major, pair_of, rewrite
from .changelog import add_change_log_row, escape, release_section, table_row
from .errors import FlowError
from .repo import MAIN
from .versions import ACCEPTANCE_HEADINGS, parse_tag, plan_path, section_lines, tables

STATUS = {"en": "Accepted by Troy on {date}", "zh-CN": "Troy 已于 {date} 验收"}
RESULT = {"en": "Accepted as {tag}", "zh-CN": "已验收为 {tag}"}
CHANGE = {"en": "Accepted by Troy as {tag}.", "zh-CN": "Troy 验收为 {tag}。"}
NONE = {"en": "None", "zh-CN": "无"}
HEADER = {"en": ("Date", "Result", "Troy's notes"), "zh-CN": ("日期", "结果", "Troy 的备注")}
_EMPTY = ("", "none", "无", "-")
_NONE_LINES = ("none", "none.", "无", "无。")


def check_tag(tag: str) -> str:
    """Checks --tag: vMAJOR.MINOR.PATCH.

    Raises:
        FlowError: The tag is not of that form.
    """
    if parse_tag(tag) is None:
        raise FlowError(f"--tag {tag!r} is not a tag of the form vMAJOR.MINOR.PATCH")
    return tag


def _notes_text(path: str) -> str:
    """Reads the notes file as one line.

    Raises:
        FlowError: The file cannot be read as UTF-8.
    """
    try:
        text = Path(path).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FlowError(f"cannot read {path}: {exc}") from exc
    return escape(text)


def add_acceptance_row(text: str, cells: list[str], lang: str) -> str | None:
    """Adds a row to the acceptance record, dropping placeholder rows (design 5.7).

    Returns:
        The new text, or None when the document has no acceptance record heading.
    """
    lines = text.split("\n")
    span = section_lines(lines, ACCEPTANCE_HEADINGS)
    if span is None:
        return None
    first, end = span[0] + 1, span[1]
    body = [line.rstrip("\r") for line in lines[first:end]]
    found = tables(body)
    ending = "\r" if lines[span[0]].endswith("\r") else ""
    if not found:
        table = [row + ending for row in ("| " + " | ".join(HEADER[lang]) + " |",
                                          "| --- | --- | --- |", table_row(cells, 3))]
        at = next((first + i for i, line in enumerate(body)
                   if line.strip().lower() in _NONE_LINES), None)
        if at is None:
            lines[first:first] = [ending] + table
        else:
            lines[at:at + 1] = table
        return "\n".join(lines)
    start, header, rows = found[0]
    width = len(header)
    keep = [first + start + 2 + i for i, row in enumerate(rows)
            if not all(cell.strip().lower() in _EMPTY for cell in row)]
    removed = [first + start + 2 + i for i in range(len(rows))
               if first + start + 2 + i not in keep]
    last = first + start + 1 + len(rows)
    ending = "\r" if lines[last].endswith("\r") else ending
    lines.insert(last + 1, table_row(cells, width) + ending)
    for index in sorted(removed, reverse=True):
        del lines[index]
    return "\n".join(lines)


def run_accept_version(args) -> tuple[dict, int]:
    """Records Troy's acceptance of a version in its test plan and the mirror.

    Args:
        args: Parsed options: tag, notes_file, date, and repo.

    Returns:
        The report and the exit code: 1, and nothing changed, when a file,
        its header, or its acceptance record is missing, or the versions differ.
    """
    tag = check_tag(args.tag)
    date = check_date(args.date)
    notes = _notes_text(args.notes_file)
    repo = git.need_repo(args.repo)
    doc = plan_path(parse_tag(tag)[0])
    report = {"command": "accept-version", "ok": False, "notes": [], "problems": [], "tag": tag,
              "plan": doc}
    pair = pair_of(repo.root, doc)
    found = [header_of(repo.root / p) for p in pair] if pair else []
    if not pair or any(f is None for f in found):
        report["problems"] = [f"{doc} or its mirror is missing or has no troy-doc header with "
                              "lang and version."]
        return report, 1
    versions = {f[1]["version"] for f in found}
    if len(versions) != 1:
        report["problems"] = [f"{pair[0]} and {pair[1]} have different versions: "
                              f"{', '.join(sorted(versions))}."]
        return report, 1
    old = versions.pop()
    new = next_major(old)
    texts = {}
    for path, (text, fields) in zip(pair, found):
        lang = fields["lang"] if fields["lang"] in STATUS else "en"
        cells = [date, RESULT[lang].format(tag=tag), notes or NONE[lang]]
        updated = add_acceptance_row(text, cells, lang)
        if updated is None:
            report["problems"] = [f"{path} has no acceptance record section."]
            return report, 1
        updated = rewrite(updated, {"version": new, "updated": date,
                                    "status": STATUS[lang].format(date=date)})
        logged = add_change_log_row(updated, new, date, CHANGE[lang].format(tag=tag))
        if logged is None:
            report["notes"].append(f"{path} has no change log table; no row was added.")
        texts[path] = logged or updated
    for path, text in texts.items():
        (repo.root / path).write_bytes(text.encode("utf-8"))
    report.update(ok=True, plan=pair[0], mirror=pair[1], version={"from": old, "to": new},
                  updated=date, changed=list(pair))
    return report, 0


def run_release_notes(args) -> tuple[dict, int]:
    """Writes the tag's section of CHANGELOG.md on origin/main to --out (design 5.7).

    Returns:
        The report and the exit code: 1 when the changelog or its section is missing.
    """
    tag = check_tag(args.tag)
    repo = git.need_repo(args.repo)
    report = {"command": "release-notes", "ok": False, "notes": [], "problems": [], "tag": tag,
              "source": "CHANGELOG.md", "out": args.out}
    text = git.read(repo, MAIN, "CHANGELOG.md") if git.commit_of(repo, MAIN) else None
    if text is None:
        report["problems"] = ["CHANGELOG.md is not on origin/main."]
        return report, 1
    section = release_section(text, tag)
    if section is None:
        report["problems"] = [f"CHANGELOG.md on origin/main has no section for {tag}."]
        return report, 1
    try:
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(section)
    except OSError as exc:
        raise FlowError(f"cannot write {args.out}: {exc}") from exc
    report["ok"] = True
    return report, 0
