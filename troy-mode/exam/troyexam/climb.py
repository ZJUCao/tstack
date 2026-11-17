"""A hillclimb's decision log (design 8.3), climb/<name>/decision.tsv in the work root."""

from pathlib import Path

COLUMNS = ("id", "hypothesis", "change", "before", "after", "delta", "gate", "verdict", "note")
VERDICTS = ("kept", "reverted")


def add_row(path: Path, row: dict) -> None:
    """Adds one attempt, with the header line first in a new log.

    Raises:
        ValueError: The verdict is not "kept" or "reverted".
    """
    if row.get("verdict") not in VERDICTS:
        raise ValueError(f"verdict must be kept or reverted, not {row.get('verdict')!r}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    cells = [str(row.get(c, "")).replace("\t", " ").replace("\n", " ") for c in COLUMNS]
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        if new:
            handle.write("\t".join(COLUMNS) + "\n")
        handle.write("\t".join(cells) + "\n")
