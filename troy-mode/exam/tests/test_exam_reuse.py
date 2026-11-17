"""Reuse group (F16 design 8.2, 14.1): when the base's runs are reused.

The base's runs are reused only when the case's version, the base's
instruction hash, the CLI version, the model IDs, and the effort all match,
the run is not void, and it is at most 14 days old. Each condition breaks
reuse on its own. The rows are also read back from a case log, as the exam
reads them.

Planted bug of design 14.2 caught here:

- "reuse with a different CLI version": ReusableTests.test_each_condition_breaks_reuse_alone
  (the "cli" subtest) and test_a_newer_cli_is_not_reused.
"""

import unittest
from datetime import datetime, timedelta, timezone

from exam_helpers import HAIKU, SONNET, new_dir
from troyexam.reuse import FIELDS, MAX_AGE, append_log, read_log, reusable

HASH = "3f9c2a1b7e04" + "a" * 52
NOW = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
CONTRACT_FIELDS = ("exam", "run", "time", "side", "case_version", "instructions", "cli", "models",
                   "effort", "status", "passed", "cost", "minutes")


def row(**changes) -> dict:
    """A base run of 2026-11-18 that every check below accepts unless changed."""
    data = {"exam": "2026-11-18-1", "run": "r01", "time": "2026-11-18T09:30:00Z",
            "side": "base", "case_version": 1, "instructions": HASH, "cli": "2.1.325",
            "models": f"{HAIKU},{SONNET}", "effort": "high", "status": "ok", "passed": True,
            "cost": 0.31, "minutes": 2.7}
    data.update(changes)
    return data


def check(data: dict, **changes) -> bool:
    """reusable() for today's exam, with the wanted values changed."""
    wanted = dict(case_version=1, instructions=HASH, cli="2.1.325", models=[HAIKU, SONNET],
                  effort="high", now=NOW)
    wanted.update(changes)
    return reusable(data, **wanted)


class ReusableTests(unittest.TestCase):
    """reusable (design 8.2)."""

    def test_a_matching_run_is_reused(self):
        """Every condition holds."""
        self.assertTrue(check(row()))

    def test_each_condition_breaks_reuse_alone(self):
        """The case version, the hash, the CLI, the models, the effort, void, and age."""
        broken = {
            "case_version": (row(), dict(case_version=2)),
            "instructions": (row(), dict(instructions="b" * 64)),
            "cli": (row(), dict(cli="2.1.326")),
            "models": (row(), dict(models=[HAIKU, "claude-sonnet-4-6-20260101"])),
            "effort": (row(), dict(effort="max")),
            "void": (row(status="void", passed=None), {}),
            "age": (row(time="2026-11-05T09:59:59Z"), {}),
        }
        for name, (data, changes) in broken.items():
            with self.subTest(condition=name):
                self.assertFalse(check(data, **changes))

    def test_a_newer_cli_is_not_reused(self):
        """The row was made by 2.1.300; today's CLI is 2.1.325 (design 14.2)."""
        self.assertFalse(check(row(cli="2.1.300")))

    def test_the_full_hash_must_match(self):
        """Equal first 12 characters are not enough."""
        self.assertFalse(check(row(), instructions="3f9c2a1b7e04" + "b" * 52))

    def test_models_are_a_set(self):
        """Order does not matter; a missing or extra model does."""
        self.assertTrue(check(row(models=f"{SONNET},{HAIKU}")))
        self.assertFalse(check(row(models=SONNET)))
        self.assertFalse(check(row(), models=[HAIKU, SONNET, "claude-opus-4-1-20250805"]))

    def test_fourteen_days_is_the_limit(self):
        """Exactly 14 days old is reused; one second more is not."""
        self.assertEqual(MAX_AGE, timedelta(days=14))
        self.assertTrue(check(row(time="2026-11-06T10:00:00Z")))
        self.assertFalse(check(row(time="2026-11-06T09:59:59Z")))

    def test_failed_and_capped_runs_are_reused(self):
        """A run that failed, or hit its cap, still measured the base."""
        self.assertTrue(check(row(passed=False)))
        self.assertTrue(check(row(status="cap", passed=False)))


class LogTests(unittest.TestCase):
    """read_log and append_log: cases/<case ID>.tsv (design 11.1)."""

    def test_missing_log_is_empty(self):
        """No file: no rows."""
        self.assertEqual(read_log(new_dir("log") / "dv-x.tsv"), [])

    def test_rows_round_trip_with_a_header(self):
        """A header line of FIELDS first, then one tab-separated line per row."""
        self.assertEqual(tuple(FIELDS), CONTRACT_FIELDS)
        path = new_dir("log") / "cases" / "dv-x.tsv"
        path.parent.mkdir(parents=True)
        append_log(path, row(run="r01"))
        append_log(path, row(run="r02", side="head", passed=False))
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "\t".join(CONTRACT_FIELDS))
        self.assertEqual(len(lines), 3)
        rows = read_log(path)
        self.assertEqual([r["run"] for r in rows], ["r01", "r02"])
        self.assertEqual([r["side"] for r in rows], ["base", "head"])
        self.assertEqual(str(rows[0]["case_version"]), "1")
        self.assertEqual(rows[0]["instructions"], HASH)

    def test_rows_read_back_are_reusable(self):
        """The types read from the file work with reusable()."""
        path = new_dir("log") / "dv-y.tsv"
        append_log(path, row())
        append_log(path, row(run="r02", cli="2.1.300"))
        rows = read_log(path)
        self.assertEqual([check(r) for r in rows], [True, False])


if __name__ == "__main__":
    unittest.main()
