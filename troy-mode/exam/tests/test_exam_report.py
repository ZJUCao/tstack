"""The PR's exam section and the hillclimb log (F16 design 8.3, 9.3).

block() prints design 9.3's section exactly; role_title() names a role as the
table does; climb.add_row() keeps decision.tsv with one row per attempt.
"""

import unittest

from exam_helpers import new_dir
from troyexam.climb import COLUMNS, add_row
from troyexam.report import block, role_title

REPORT = r"D:\Troy\troy-mode-work\results\2026-11-20-1\report.md"
DESIGN_BLOCK = (
    "## Role exam\n"
    "\n"
    "Result: passed\n"
    "Instructions: 3f9c2a1b7e04\n"
    "Cases: 2 run, 10 not affected\n"
    "Runs: 20, 10 of them reused from the base; $14.20; 1 h 05 min\n"
    "\n"
    "| Case | Role | Base | Head | Result |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| dv-mock-notes | Developer | 2 of 5 | 5 of 5 | fixed |\n"
    "| dv-impl-notes | Developer | 4 of 5 | 5 of 5 | not worse |\n"
    "\n"
    f"Report: {REPORT}\n")


def summary(**changes) -> dict:
    """The summary behind design 9.3's example."""
    data = {"result": "passed", "instructions": "3f9c2a1b7e04" + "5d" * 26,
            "cases_run": 2, "cases_not_affected": 10, "runs": 20, "reused": 10, "cost": 14.2,
            "minutes": 65,
            "rows": [{"case": "dv-mock-notes", "role": "developer", "base": 2, "head": 5, "of": 5,
                      "result": "fixed"},
                     {"case": "dv-impl-notes", "role": "developer", "base": 4, "head": 5, "of": 5,
                      "result": "not worse"}],
            "report": REPORT}
    data.update(changes)
    return data


class BlockTests(unittest.TestCase):
    """block (design 9.3)."""

    def test_the_designs_example(self):
        """Exactly the section the design shows."""
        self.assertEqual(block(summary()), DESIGN_BLOCK)

    def test_ten_runs_a_case_and_other_roles(self):
        """A case that ran 5 more times shows "of 10"; roles are title case."""
        rows = [{"case": "if-example-format", "role": "interface-designer", "base": 9, "head": 6,
                 "of": 10, "result": "worse"},
                {"case": "cr-mock-review", "role": "code-reviewer", "base": 5, "head": 5, "of": 5,
                 "result": "not worse"}]
        text = block(summary(result="failed", rows=rows, minutes=125, cost=3.456))
        self.assertIn("Result: failed\n", text)
        self.assertIn("| if-example-format | Interface Designer | 9 of 10 | 6 of 10 | worse |\n",
                      text)
        self.assertIn("| cr-mock-review | Code Reviewer | 5 of 5 | 5 of 5 | not worse |\n", text)
        self.assertIn("; $3.46; 2 h 05 min\n", text)

    def test_accepted_by_troy(self):
        """A failed exam that Troy accepted keeps the date and the reason (design 7.2)."""
        result = "failed, accepted by Troy on 2026-11-21: the judge misread one report"
        self.assertIn(f"Result: {result}\n", block(summary(result=result)))

    def test_no_case_affected(self):
        """Result no case affected, nothing run, nothing spent."""
        text = block(summary(result="no case affected", cases_run=0, cases_not_affected=12,
                             runs=0, reused=0, cost=0.0, minutes=0, rows=[]))
        lines = text.split("\n")
        self.assertEqual(lines[:2], ["## Role exam", ""])
        self.assertIn("Result: no case affected", lines)
        self.assertIn("Instructions: 3f9c2a1b7e04", lines)
        self.assertIn("Cases: 0 run, 12 not affected", lines)
        self.assertIn("Runs: 0, 0 of them reused from the base; $0.00; 0 h 00 min", lines)
        self.assertFalse([line for line in lines if line.startswith("| dv-")])
        self.assertTrue(text.endswith(f"Report: {REPORT}\n"))

    def test_role_title(self):
        """Each role's name in the table."""
        expected = {"architect": "Architect", "interface-designer": "Interface Designer",
                    "test-manager": "Test Manager", "developer": "Developer",
                    "test-engineer": "Test Engineer", "code-reviewer": "Code Reviewer"}
        for role, title in expected.items():
            with self.subTest(role=role):
                self.assertEqual(role_title(role), title)


class ClimbTests(unittest.TestCase):
    """add_row: decision.tsv of a hillclimb (design 8.3)."""

    def test_rows_with_a_header(self):
        """The nine columns as the header, then one tab-separated row per attempt."""
        self.assertEqual(tuple(COLUMNS), ("id", "hypothesis", "change", "before", "after",
                                          "delta", "gate", "verdict", "note"))
        path = new_dir("climb") / "notes" / "decision.tsv"
        path.parent.mkdir(parents=True)
        add_row(path, {"id": "1", "hypothesis": "a fixed sentence, because notes drifted",
                       "change": "DV1 brief", "before": "2", "after": "5", "delta": "3",
                       "gate": "held", "verdict": "kept", "note": ""})
        add_row(path, {"id": "2", "hypothesis": "a shorter step 2", "change": "agent file",
                       "before": "5", "after": "4", "delta": "-1", "gate": "held",
                       "verdict": "reverted", "note": "no gain"})
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "\t".join(COLUMNS))
        self.assertEqual(lines[1].split("\t"), ["1", "a fixed sentence, because notes drifted",
                                                "DV1 brief", "2", "5", "3", "held", "kept", ""])
        self.assertEqual(lines[2].split("\t")[7:], ["reverted", "no gain"])
        self.assertEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
