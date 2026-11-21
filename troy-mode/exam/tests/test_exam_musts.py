"""Which universal checks are musts (F16 design 4.3 version 1.5, D152 as refined on 2026-11-18).

U1, U2, U3, U4, U6, and U7 are musts. U4 became one in the PR that lands
tstack#64's hook, R23 (F05 design 8.3). U5 is a note while the hook that fixes
it is pending (tstack#49): it is checked and reported on every run, but a run
that fails only U5 still passes its checks by script.
"""

import unittest
from types import SimpleNamespace

import exam_helpers  # noqa: F401  (puts troyexam on the import path)
from troyexam.cases import Criterion
from troyexam.checks import UNIVERSAL, UNIVERSAL_MUSTS, UNIVERSAL_NOTES
from troyexam.exam import Exam


def record(**failed) -> dict:
    """An ok run record whose criteria all pass but the ones named false."""
    criteria = {name: {"passed": True, "evidence": "fine"} for name in (*UNIVERSAL, "stub")}
    for name in failed:
        criteria[name] = {"passed": False, "evidence": "failed"}
    return {"status": "ok", "criteria": criteria}


CASE = SimpleNamespace(criteria=[Criterion("stub", "mock_bodies_only_raise", None, True, {}),
                                 Criterion("doc", None, 1, True, {}),
                                 Criterion("extra", "result_is", None, False, {"want": "done"})])


class UniversalMustsTests(unittest.TestCase):
    """The split of design 4.3 and what it does to a run's grade."""

    def test_the_musts_and_the_notes(self):
        """Six musts, U4 among them, one note, U5, and together the seven universal checks."""
        self.assertEqual(UNIVERSAL_MUSTS, ("U1", "U2", "U3", "U4", "U6", "U7"))
        self.assertEqual(UNIVERSAL_NOTES, ("U5",))
        self.assertEqual(sorted(UNIVERSAL_MUSTS + UNIVERSAL_NOTES), sorted(UNIVERSAL))

    def test_a_note_alone_does_not_fail_a_run(self):
        """Failing U5, or a case check that is a note, leaves the run's checks by script passing."""
        for failed in ({"U5": 1}, {"extra": 1}, {"U5": 1, "extra": 1}):
            with self.subTest(failed=sorted(failed)):
                self.assertTrue(Exam._scripts_ok(CASE, record(**failed)))

    def test_failing_only_u4_fails_a_run(self):
        """U4 is a must since version 1.5: failing it, alone or with U5, fails the run by script."""
        for failed in ({"U4": 1}, {"U4": 1, "U5": 1}, {"U4": 1, "extra": 1}):
            with self.subTest(failed=sorted(failed)):
                self.assertFalse(Exam._scripts_ok(CASE, record(**failed)))

    def test_a_must_fails_a_run(self):
        """Failing any universal must, or the case's must check, fails the run."""
        for name in (*UNIVERSAL_MUSTS, "stub"):
            with self.subTest(failed=name):
                self.assertFalse(Exam._scripts_ok(CASE, record(**{name: 1})))

    def test_a_run_that_did_not_finish_fails(self):
        """A cap, a time-out, or a void run never passes by script."""
        for status in ("cap", "timeout", "void"):
            with self.subTest(status=status):
                rec = record()
                rec["status"] = status
                self.assertFalse(Exam._scripts_ok(CASE, rec))


if __name__ == "__main__":
    unittest.main()
