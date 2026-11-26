"""The sample of spot checks (F18 design 7.1, 7.4, 13.1 "Spot checks"; part 2 contract 3, 5, 9).

One feature in ``spot_check_every``, counted in the topological order from the first feature
after the first ``troy_approves_first``, is in the sample. ``status`` gives the report's
``spot`` (on, configured, every, approves_first, sample, off_due) and each feature's
``spot``: null unless spot checks are on and the feature is past the approved ones, else
``sample`` or ``none``. The setting is read from ``.troy-mode/config.toml`` on
``origin/main``.

Planted bug of design 13.2 caught here:

- "the sample counted from the first feature instead of after the approved ones":
  ``SampleFunctionTests.test_contract_examples``, ``test_counted_after_the_approved_ones``,
  and ``SpotReportTests.test_three_by_three`` and ``test_every_two``.
"""

import unittest

from flow_helpers import CONFIG, Fakes, Feature, Project, base_step, config_text
from spot_helpers import (
    CACHE, CHAIN, EVIDENCE_CASES, OFF_BRANCH, SPOT_HEADING, TM_HEADING, Case, SpotCase, flow,
    run_cases, spot_files, spot_module,
)

IDS = [item.id for item in CHAIN]
TWENTY = [f"F{n:02d}" for n in range(1, 21)]
PARTS = tuple(Feature(f"F{n:02d}", f"Part {n}") for n in range(1, 7))
REVERSED = ["F06", "F05", "F04", "F03", "F02", "F01"]


def spot_value(on, configured, every, approves, sample, off_due=None) -> dict:
    """The report's ``spot`` (contract 5)."""
    return {"on": on, "configured": configured, "every": every, "approves_first": approves,
            "sample": sample, "off_due": off_due}


class SampleFunctionTests(unittest.TestCase):
    """``troyflow.spot.sample`` and the module's constants (contract 3 and 9)."""

    @classmethod
    def setUpClass(cls):
        """Imports the module once; a missing module fails each test, not the class."""
        try:
            cls.spot, cls.missing = spot_module(), None
        except AssertionError as exc:
            cls.spot, cls.missing = None, str(exc)

    def module(self):
        """The module, or a failure that says why it could not be imported."""
        if self.spot is None:
            self.fail(self.missing)
        return self.spot

    def test_contract_examples(self):
        """Planted bug "the sample counted from the first feature": the contract's examples."""
        sample = self.module().sample
        self.assertEqual(sample(TWENTY, 3, 3), ["F06", "F09", "F12", "F15", "F18"])
        self.assertEqual(sample(TWENTY, 0, 3), ["F03", "F06", "F09", "F12", "F15", "F18"])
        self.assertEqual(sample(TWENTY[:10], 7, 2), ["F09"])

    def test_counted_after_the_approved_ones(self):
        """Planted bug "the sample counted from the first feature": with one approved feature
        and every 3, F04 and F07, not F03 and F06."""
        sample = self.module().sample
        self.assertEqual(sample(TWENTY[:7], 1, 3), ["F04", "F07"])
        self.assertEqual(sample(TWENTY[:6], 2, 2), ["F04", "F06"])

    def test_follows_the_order_given(self):
        """The order, not the IDs' sort, decides: the reversed order samples F04 and F02."""
        self.assertEqual(self.module().sample(REVERSED, 1, 2), ["F04", "F02"])

    def test_approved_at_or_past_the_order_gives_nothing(self):
        """``approves_first`` at or past the number of features: an empty sample."""
        sample = self.module().sample
        self.assertEqual(sample(TWENTY[:5], 5, 2), [])
        self.assertEqual(sample(TWENTY[:5], 9, 2), [])
        self.assertEqual(sample([], 0, 3), [])

    def test_constants(self):
        """The headings, the cases of E3, the cache, and the branch of ``spot-off``."""
        spot = self.module()
        self.assertEqual((spot.SPOT_HEADING, spot.TM_RULING_HEADING, spot.CACHE, spot.OFF_BRANCH),
                         (SPOT_HEADING, TM_HEADING, CACHE, OFF_BRANCH))
        self.assertEqual(tuple(spot.EVIDENCE_CASES), EVIDENCE_CASES)


def branch_only_case() -> Case:
    """``spot_checks = true`` committed on the work branch only, not on origin/main."""
    return Case([base_step(spot_files(CHAIN, flow(1)))])


CASES = {
    "off": Case([base_step(spot_files(CHAIN))]),
    "three by three": Case([base_step(spot_files(CHAIN, flow(3, True, 3)))]),
    "zero": Case([base_step(spot_files(CHAIN, flow(0, True, 3)))]),
    "past the features": Case([base_step(spot_files(CHAIN, flow(12, True, 3)))]),
    "every two": Case([base_step(spot_files(CHAIN, flow(1, True, 2)))]),
    "configured false": Case([base_step(spot_files(CHAIN, flow(1, False, 2)))]),
    "order line": Case([base_step(spot_files(PARTS, flow(1, True, 2), order=REVERSED))]),
}


class SpotReportTests(SpotCase):
    """The report's ``spot`` and each feature's ``spot`` (contract 3 and 5)."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case, side by side, and once with the setting on a branch."""
        cls.outs = run_cases(CASES)
        clone = Project(branch_only_case().steps)
        clone.commit("[rules] Turn on spot checks",
                     {CONFIG: config_text(extra=flow(1, True, 2))})
        cls.outs["only on the branch"] = (clone.status(fakes=Fakes()), None, clone)

    def spots(self, name: str, sampled=(), first: int = 0) -> None:
        """Asserts each feature's ``spot``: null for the first ones, else sample or none."""
        expected = [(fid, None if index < first else ("sample" if fid in sampled else "none"))
                    for index, fid in enumerate(IDS)]
        self.assertEqual(self.feature_spots(name), expected)

    def test_off_by_default(self):
        """No ``[flow]`` table: spot checks off, every 3, the count 3, no sample, and every
        feature's ``spot`` null."""
        self.assertEqual(self.spot("off"), spot_value(False, False, 3, 3, []))
        self.assertEqual(self.feature_spots("off"), [(fid, None) for fid in IDS])

    def test_three_by_three(self):
        """Planted bug "counted from the first feature": three approved, every 3: F06, F09."""
        self.assertEqual(self.spot("three by three"),
                         spot_value(True, True, 3, 3, ["F06", "F09"]))
        self.spots("three by three", ("F06", "F09"), first=3)

    def test_none_approved(self):
        """``troy_approves_first = 0``: F03, F06, F09, counted from the first feature."""
        self.assertEqual(self.spot("zero"), spot_value(True, True, 3, 0, ["F03", "F06", "F09"]))
        self.spots("zero", ("F03", "F06", "F09"))

    def test_approved_past_the_features(self):
        """A count past the ten features: no sample, and every feature's ``spot`` null."""
        self.assertEqual(self.spot("past the features"), spot_value(True, True, 3, 12, []))
        self.assertEqual(self.feature_spots("past the features"), [(fid, None) for fid in IDS])

    def test_every_two(self):
        """Planted bug "counted from the first feature": one approved, every 2: F03, F05, F07,
        F09."""
        self.assertEqual(self.spot("every two"),
                         spot_value(True, True, 2, 1, ["F03", "F05", "F07", "F09"]))
        self.spots("every two", ("F03", "F05", "F07", "F09"), first=1)

    def test_configured_false_keeps_the_number(self):
        """``spot_checks = false`` with every 2: off, no sample, the number still reported."""
        self.assertEqual(self.spot("configured false"), spot_value(False, False, 2, 1, []))
        self.assertEqual(self.feature_spots("configured false"), [(fid, None) for fid in IDS])

    def test_sample_follows_the_order_line(self):
        """The order line F06 to F01: F04 and F02, in the order's order."""
        self.assertEqual(self.spot("order line")["sample"], ["F04", "F02"])
        spots = dict(self.feature_spots("order line"))
        self.assertEqual(spots, {"F06": None, "F05": "none", "F04": "sample", "F03": "none",
                                 "F02": "sample", "F01": "none"})

    def test_setting_is_read_from_origin_main(self):
        """``spot_checks = true`` committed on the work branch only: not configured."""
        self.assertEqual(self.spot("only on the branch"), spot_value(False, False, 3, 1, []))


if __name__ == "__main__":
    unittest.main()
