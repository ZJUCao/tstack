"""Troy's approval, recorded in a document's header and its mirror's (F07 design 8.6, D61).

Three front matter lines change: version moves to the next major (F01 design
section 4), updated becomes the date, and status says who approved it. The
document's change log also gets a row for the new version (F08 D77). When
either file of the pair has no change-log table, nothing changes and the
command exits 1 (F07 D201), and so do accept-version and rule-row. Approving
the architecture also accepts the proposed ADRs it lists (F07 D202).
"""

import datetime
import re
from pathlib import Path

from troycheck.frontmatter import parse_header, version_key

from . import adrs, repo as git
from .changelog import add_change_log_row
from .errors import FlowError

STATUS = {"en": "Approved by Troy on {date}", "zh-CN": "Troy 已于 {date} 批准"}
CHANGE = {"en": "Approved by Troy.", "zh-CN": "Troy 批准。"}
_LINE = re.compile(r'^(?P<key>version|updated|status):(?P<space>[ \t]*)"(?P<value>.*)"'
                   r"(?P<end>[ \t]*\r?)$")


def no_change_log(path: str) -> str:
    """The problem for a file without a change-log table (F07 D201)."""
    return (f'{path} has no change log table under a "Change log" or "修改记录" heading; '
            "nothing was changed.")


def check_date(text: str | None) -> str:
    """Returns --date, or today, as YYYY-MM-DD.

    Raises:
        FlowError: The date is not a real YYYY-MM-DD date.
    """
    if text is None:
        return datetime.date.today().isoformat()
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            raise ValueError(text)
        return datetime.date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise FlowError(f"--date {text!r} is not a YYYY-MM-DD date") from exc


def next_major(version: str) -> str:
    """Returns the next major version, for example "1.0" for "0.3"."""
    return f"{version_key(version)[0] + 1}.0"


def header_of(path: Path) -> tuple[str, dict] | None:
    """Reads a document and its front matter fields, or None when it has no usable header."""
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    header = parse_header(text)
    if header is None or not all(k in header.fields for k in ("troy-doc", "lang", "version")):
        return None
    if version_key(header.fields["version"]) is None:
        return None
    return text, header.fields


def rewrite(text: str, values: dict[str, str]) -> str:
    """Replaces the values of some quoted front matter lines and keeps every other byte."""
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r") == "---"), len(lines))
    for index in range(1, end):
        match = _LINE.match(lines[index])
        if match and match.group("key") in values:
            lines[index] = (f'{match.group("key")}:{match.group("space")}"'
                            f'{values[match.group("key")]}"{match.group("end")}')
    return "\n".join(lines)


def pair_of(root: Path, doc: str) -> tuple[str, str] | None:
    """Finds the English document and its mirror from either one's header."""
    found = header_of(root / doc)
    if found is None:
        return None
    fields, folder = found[1], str(Path(doc).parent).replace("\\", "/")
    link = fields.get("mirror") if fields["lang"] == "en" else fields.get("mirror-of")
    if not link:
        return None
    other = link if folder in ("", ".") else f"{folder}/{link}"
    return (doc, other) if fields["lang"] == "en" else (other, doc)


def run_approve(args) -> tuple[dict, int]:
    """Records Troy's approval in a document and its mirror.

    Args:
        args: Parsed options: doc, date, and repo.

    Returns:
        The report and the exit code: 1, and nothing changed, when a header
        or the mirror is missing, the versions differ, either file has no
        change-log table (D201), or a listed ADR lacks a file (D202).
    """
    date = check_date(args.date)
    repo = git.need_repo(args.repo)
    doc = args.doc.replace("\\", "/")
    report = {"command": "approve", "ok": False, "notes": [], "problems": [], "doc": doc}
    pair = pair_of(repo.root, doc)
    found = [header_of(repo.root / p) for p in pair] if pair else []
    if not pair or any(f is None for f in found):
        report["problems"] = [f"{doc} or its mirror is missing or has no troy-doc header "
                              "with lang and version."]
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
        status = STATUS[lang].format(date=date)
        updated = rewrite(text, {"version": new, "updated": date, "status": status})
        texts[path] = add_change_log_row(updated, new, date, CHANGE[lang])
    report["problems"] = [no_change_log(path) for path, text in texts.items() if text is None]
    accepted, adr_texts = [], {}
    if found[0][1].get("troy-doc") == adrs.ARCHITECTURE:
        accepted, adr_texts, problems = _accept_adrs(repo.root, [f[0] for f in found], date)
        report["problems"] += problems
    if report["problems"]:
        return report, 1
    for path, (text, fields) in zip(pair, found):
        if accepted:
            lang = fields["lang"] if fields["lang"] in STATUS else "en"
            texts[path] = adrs.accept_rows(texts[path], lang, set(accepted))
    texts.update(adr_texts)
    for path, text in texts.items():
        (repo.root / path).write_bytes(text.encode("utf-8"))
    report.update(ok=True, doc=pair[0], mirror=pair[1], version={"from": old, "to": new},
                  updated=date, changed=list(texts), change_log=list(pair), adrs=accepted)
    return report, 0


def _accept_adrs(root: Path, architecture: list[str], date: str
                 ) -> tuple[list[str], dict[str, str], list[str]]:
    """Accepts the proposed ADRs that the architecture lists, in both languages (D202).

    Args:
        root: The project folder.
        architecture: The architecture's English text and its mirror's.
        date: The approval's date.

    Returns:
        The accepted IDs in ID order, the new text of each of their files
        (English, then mirror), and the problems that stop the approval.
    """
    ids = sorted({adr for text in architecture for adr in adrs.listed_ids(text)})
    accepted, texts, problems = [], {}, []
    for adr in ids:
        english = adrs.adr_files(root, adr)
        if len(english) != 1:
            problems.append(f"{adr} is listed in the architecture, but docs/adr/ has "
                            f"{'no' if not english else 'more than one'} English file for it.")
            continue
        pair = pair_of(root, english[0])
        found = [header_of(root / p) for p in pair] if pair else []
        if not pair or any(f is None for f in found):
            problems.append(f"{adr}: {english[0]} or its mirror is missing or has no troy-doc "
                            "header with lang and version.")
            continue
        versions = {f[1]["version"] for f in found}
        if len(versions) != 1:
            problems.append(f"{adr}: {pair[0]} and {pair[1]} have different versions: "
                            f"{', '.join(sorted(versions))}.")
            continue
        langs = [f[1]["lang"] if f[1]["lang"] in STATUS else "en" for f in found]
        if not any(adrs.is_proposed(f[0], lang) for f, lang in zip(found, langs)):
            continue
        new = next_major(versions.pop())
        for path, (text, _), lang in zip(pair, found, langs):
            text = adrs.accept_status(text, lang, date)
            texts[path] = rewrite(text, {"version": new, "updated": date,
                                         "status": STATUS[lang].format(date=date)})
        accepted.append(adr)
    return accepted, texts, problems
