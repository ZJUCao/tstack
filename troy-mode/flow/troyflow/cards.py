"""The card table: the pstack skills that a task's brief names (F17 design 4, D162).

For a task with rows, `brief` adds each card's absolute path to Read first and one
fixed line of troy-mode's to the Task field. The role reads the card as tstack ships
it; troy-mode never copies or changes it. brief imports this module, so the table
and every card it names are part of F16's instruction set (F17 design 5, D163).
"""

from dataclasses import dataclass
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Row:
    """One card for one task.

    Attributes:
        task: The task ID, such as ``TE1``.
        path: The card's ``SKILL.md``, as ``skills/<name>/SKILL.md`` from the plugin root.
        line: troy-mode's fixed line: where the card applies, and which rule wins.
    """

    task: str
    path: str
    line: str


ROWS: tuple[Row, ...] = (
    Row(
        task="AR2",
        path="skills/principle-prove-it-works/SKILL.md",
        line=(
            "run each check that the project's CI runs on the design file, with the"
            " project's settings, such as `ruff format --check` on its python blocks"
            " when CI formats them, and give each command and its output in Checks."
            " Run them on the working tree as it is, with no git command that changes"
            " anything, in the project or in a copy of it; a check that needs a commit,"
            " such as troy-check's `pr`, runs in CI on the PR."
        ),
    ),
)


def name(row: Row) -> str:
    """The card's folder name, ``<name>`` of ``skills/<name>/SKILL.md``."""
    return row.path.split("/")[1]


def rows_for(task: str, rows: tuple[Row, ...] | None = None) -> list[Row]:
    """The rows of one task, in table order."""
    return [row for row in (ROWS if rows is None else rows) if row.task == task]


def absolute(row: Row) -> str:
    """The card's absolute path in the plugin, in POSIX form, for Read first."""
    return (PLUGIN / row.path).as_posix()


def sentence(row: Row) -> str:
    """The text the Task field gains for one card."""
    return f"Apply `{name(row)}`: {row.line}"


def problems(task: str, rows: tuple[Row, ...] | None = None) -> list[str]:
    """One problem for each card of the task that the plugin does not hold."""
    return [f"card: {row.path} is not in the plugin (F17 design 4.1)."
            for row in rows_for(task, rows) if not (PLUGIN / row.path).is_file()]
