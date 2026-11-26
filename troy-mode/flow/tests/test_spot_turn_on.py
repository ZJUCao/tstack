"""Turning spot checks on after F07 merged some earlier designs (F18 design 7.4).

Added by F18 part 2's build after its trial: turning spot checks on sets
``troy_approves_first`` to the features accepted so far. Some of them may have had their PR 1
and PR 2 merged by F07 under a smaller count, so their design and test plan stay below 1.0.
Their approval is not Troy's to record, so ``status`` must not ask for
``[docs] Record Troy's approval of ...`` for an accepted feature; the next feature comes
next. In the trial, the old rule asked to record an approval of F05's test plan, and the
session lowered the count instead, which moved the sample. The same holds after ``spot-off``
raises the count to every feature: a sample's design that F07 merged before that ``[rules]``
PR needs no record either (the trial's F10 design, #104).
"""

import unittest

from flow_helpers import CONFIG, base_step, config_text, stages, step
from spot_helpers import APPROVALS_TITLE, CHAIN, Case, SpotCase, flow, run_cases, spot_files

FIVE = CHAIN[:5]


def history(approves: int) -> list:
    """F01 approved by Troy; F02 and F03 merged by F07 below 1.0 and accepted; then the
    ``[rules]`` PR that turns spot checks on with every 2 and the count given."""
    steps = [base_step(spot_files(FIVE, flow(1)))]
    steps += stages(FIVE[0], 6)
    steps += stages(FIVE[1], 6, design="0.2", plan="0.2")
    steps += stages(FIVE[2], 6, design="0.3", plan="0.3")
    steps.append(step(APPROVALS_TITLE, {CONFIG: config_text(extra=flow(approves, True, 2))}))
    return steps


def turned_off() -> list:
    """Spot checks on after F01; F02's design merged by F07 below 1.0 as a sample; then the
    ``[rules]`` PR of ``spot-off``: spot checks off and the count raised to every feature."""
    steps = [base_step(spot_files(FIVE, flow(1)))]
    steps += stages(FIVE[0], 6)
    steps.append(step(APPROVALS_TITLE, {CONFIG: config_text(extra=flow(1, True, 2))}))
    steps += stages(FIVE[1], 1, design="0.2")
    steps.append(step(APPROVALS_TITLE, {CONFIG: config_text(extra=flow(5, False, 2))}))
    return steps


CASES = {
    "count raised": Case(history(3)),
    "count two": Case(history(2)),
    "turned off": Case(turned_off()),
}


class TurnOnTests(SpotCase):
    """No record of an approval Troy never gave (F18 design 7.4)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case."""
        cls.outs = run_cases(CASES)

    def test_next_is_the_next_stage_not_a_record(self):
        """``troy_approves_first = 3`` with F02's and F03's documents below 1.0: F04's
        design, not a record of their approval; the sample after three is F05."""
        nxt = self.nxt("count raised")
        self.assertEqual((nxt["action"], nxt["item"], nxt["stage"], nxt["merged_by"],
                          nxt["spot"]), ("stage", "F04", 1, "f07", "none"))
        self.assertEqual(self.spot("count raised")["sample"], ["F05"])

    def test_same_history_with_the_count_at_two(self):
        """With the count at 2 (F02 accepted below 1.0) also F04's design, now sampled."""
        nxt = self.nxt("count two")
        self.assertEqual((nxt["action"], nxt["item"], nxt["stage"], nxt["spot"]),
                         ("stage", "F04", 1, "sample"))

    def test_no_record_after_spot_checks_go_off(self):
        """After ``spot-off`` raised the count, F02's design, which F07 merged before it, gets
        no record of an approval Troy never gave: F02's test plan comes next, Troy's to
        approve (found in the trial, F10's design #104)."""
        nxt = self.nxt("turned off")
        self.assertEqual((nxt["action"], nxt["item"], nxt["stage"], nxt["merged_by"]),
                         ("stage", "F02", 2, "troy"))


if __name__ == "__main__":
    unittest.main()
