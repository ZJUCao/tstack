"""Document headers and structure (F01 design section 4, design section 6.4).

A document is a Markdown file that starts with YAML front matter holding a
"troy-doc" key. Values are expected in double quotes. Only the flat
"key: value" form used by the templates is read; no YAML library is needed.
"""

import re
from dataclasses import dataclass, field

REQUIRED = ("troy-doc", "lang", "version", "updated", "status")
_VERSION = re.compile(r"\d+\.\d+")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_HEADING = re.compile(r"^(#{1,6})\s")
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Header:
    """A document's front matter.

    Attributes:
        fields: Values by key, with surrounding quotes removed.
        unquoted: Keys whose value is not in double quotes.
        body: The text after the front matter.
    """

    fields: dict[str, str]
    unquoted: list[str] = field(default_factory=list)
    body: str = ""

    @property
    def is_document(self) -> bool:
        """True when the front matter holds a troy-doc key."""
        return "troy-doc" in self.fields


def parse_header(text: str) -> Header | None:
    """Reads the front matter at the start of a Markdown file.

    Args:
        text: The whole file.

    Returns:
        The header, or None when the file does not start with front matter.
    """
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    header = Header({}, [], text[end + 4:].lstrip("-").lstrip("\n"))
    for line in text[4:end].split("\n"):
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            continue
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1].replace('\\"', '"')
        else:
            header.unquoted.append(key)
        header.fields[key] = value
    return header


def header_problems(header: Header) -> list[str]:
    """Lists what is wrong with a document header (design 6.4, point 1).

    Args:
        header: A parsed document header.

    Returns:
        One message per problem, empty when the header is valid.
    """
    f = header.fields
    problems = [f"missing field {key!r}" for key in REQUIRED if key not in f]
    problems += [f"value of {key!r} is not in double quotes" for key in header.unquoted]
    lang = f.get("lang")
    if lang not in ("en", "zh-CN"):
        problems.append(f"lang must be \"en\" or \"zh-CN\", not {lang!r}")
    elif lang == "en" and "mirror" not in f:
        problems.append("an English document needs a 'mirror' field")
    elif lang == "zh-CN" and "mirror-of" not in f:
        problems.append("a Chinese document needs a 'mirror-of' field")
    if "version" in f and not _VERSION.fullmatch(f["version"]):
        problems.append(f"version must be MAJOR.MINOR, not {f['version']!r}")
    if "updated" in f and not _DATE.fullmatch(f["updated"]):
        problems.append(f"updated must be YYYY-MM-DD, not {f['updated']!r}")
    return problems


def version_key(version: str) -> tuple[int, int] | None:
    """Turns "MAJOR.MINOR" into a comparable pair, or None if malformed."""
    if not _VERSION.fullmatch(version or ""):
        return None
    major, minor = version.split(".")
    return int(major), int(minor)


def _table_columns(line: str) -> int:
    """Counts the columns of a Markdown table row."""
    cells = line.replace("\\|", "").strip()
    return cells.count("|") - 1


def structure(body: str) -> tuple[list[int], list[int]]:
    """Describes a document's shape outside code blocks.

    Args:
        body: The document text after the front matter.

    Returns:
        The heading levels in order, and the column count of each table in
        order (taken from its first row).
    """
    headings, tables = [], []
    in_fence, in_table = False, False
    for line in body.split("\n"):
        if _FENCE.match(line):
            in_fence, in_table = not in_fence, False
            continue
        if in_fence:
            continue
        heading = _HEADING.match(line)
        if heading:
            headings.append(len(heading.group(1)))
        is_row = line.lstrip().startswith("|")
        if is_row and not in_table:
            tables.append(_table_columns(line))
        in_table = is_row
    return headings, tables
