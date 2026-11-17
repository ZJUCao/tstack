"""Each case's runs, and when the base's runs are reused (design 8.2).

cases/<case ID>.tsv in the work root holds one row per run, of any exam.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_AGE = timedelta(days=14)
FIELDS = ("exam", "run", "time", "side", "case_version", "instructions", "cli", "models",
          "effort", "status", "passed", "cost", "minutes")
TIME = "%Y-%m-%dT%H:%M:%SZ"


def _clean(value) -> str:
    """Writes one cell: lists comma-separated, no tabs or line ends."""
    if isinstance(value, (list, tuple)):
        value = ",".join(str(v) for v in value)
    if value is None:
        value = ""
    if isinstance(value, bool):
        value = "true" if value else "false"
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def read_log(path: Path) -> list[dict]:
    """Reads a case's runs; [] when the file is missing."""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    if not lines:
        return []
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:] if line.strip()]


def append_log(path: Path, row: dict) -> None:
    """Adds one run's row, with the header line first in a new file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        if new:
            handle.write("\t".join(FIELDS) + "\n")
        handle.write("\t".join(_clean(row.get(field)) for field in FIELDS) + "\n")


def parse_time(text: str) -> datetime | None:
    """Reads an ISO 8601 UTC time such as 2026-11-20T10:00:00Z; None when unreadable."""
    try:
        return datetime.strptime(text, TIME).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def models_of(row: dict) -> frozenset[str]:
    """The model IDs of a row, from its comma-separated cell or its list."""
    value = row.get("models") or ""
    items = value if isinstance(value, (list, tuple)) else str(value).split(",")
    return frozenset(item.strip() for item in items if item.strip())


def reusable(row: dict, *, case_version: int, instructions: str, cli: str,
             models: Sequence[str], effort: str, now: datetime) -> bool:
    """Tells whether a recorded run may stand in for a new run of the base.

    Every condition of design 8.2 must hold: the case's version, the full
    instruction hash, the CLI version, the set of model IDs, and the effort
    match; the run is not void; and it is at most 14 days old.
    """
    when = parse_time(str(row.get("time", "")))
    try:
        version = int(row.get("case_version", -1))
    except (TypeError, ValueError):
        return False
    if when is None or row.get("status") == "void":
        return False
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (version == case_version and row.get("instructions") == instructions
            and row.get("cli") == cli and models_of(row) == frozenset(models)
            and row.get("effort") == effort and timedelta(0) <= now - when <= MAX_AGE)


def reusable_runs(rows: Sequence[dict], **want) -> list[dict]:
    """The rows that reusable() accepts, newest first."""
    found = [row for row in rows if reusable(row, **want)]
    return sorted(found, key=lambda r: r.get("time", ""), reverse=True)
