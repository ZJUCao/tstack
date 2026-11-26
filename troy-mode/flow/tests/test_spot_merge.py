"""Who merges PR 1 and PR 2 under spot checks (F18 design 7.1, 7.2, 7.5; part 2 contract 5).

``merged_by`` of a feature's PR 1 or PR 2: Troy for the first ``troy_approves_first``
features always; for a later feature, F07 while spot checks are off (as today), Troy for a
marked PR and F07 for an unmarked one while they are on, and Troy for every one while an
overturn has turned them off (off-due). Every other title keeps today's ``merged_by``. Each
open PR gains ``spot`` and ``risky``, and every ``next`` entry gains ``spot`` and ``risky``.

Planted bugs of design 13.2 caught here:

- "a risky PR merged" (``merged_by`` f07 despite marks while on):
  ``OpenPrTests.test_merged_by_while_on`` and ``NextTests.test_marked_pr1_waits_for_troy``.
- "spot checks left on after an overturn" (``merged_by`` f07 for later PRs):
  ``OpenPrTests.test_merged_by_while_off_due`` and ``NextTests.test_off_due_pr_waits``.

``OpenPrTests.test_merged_by_without_spot_keys`` passes on today's engine: a config without
the new keys keeps today's ``merged_by``.
"""

import unittest

from flow_helpers import base_step, stages
from spot_helpers import (
    CR, ISSUE_LABELS, Case, SpotCase, all_listed, answer_step, chain, curl, flow, link_to, mark,
    open_pr, overturn_issue, ruled, run_cases, spot_files, stage_open, thread,
)

SIX = chain(6)
F1, F2, F3, F4, F5 = SIX[:5]
TYPO = "[docs] Fix a typo in the README"
OPEN = [stage_open(51, F2, 1), stage_open(52, F3, 1), stage_open(53, F4, 1),
        stage_open(54, F5, 2), stage_open(55, F3, 3), open_pr(56, TYPO, "troy-mode/typo")]
RULED_COMMENTS = {51: thread(51, *ruled()), 52: thread(52, *ruled()),
                  55: thread(55, *ruled("Architect", CR))}
LINK = link_to(52)
OFF_DUE = [overturn_issue(90, LINK)]
CONFIGS = {"no keys": flow(2), "false": flow(2, False, 2), "on": flow(2, True, 2),
           "off-due": flow(2, True, 2)}
PM7_MERGE = {"ruler": "Product Manager", "task": "PM7", "result": "merge"}


def steps(setting: str, *more) -> list:
    """Six chained features, F01 accepted, two approved by Troy, every 2: F04 and F06."""
    return [base_step(spot_files(SIX, CONFIGS[setting])), *stages(F1, 6), *more]


def fakes(setting: str, prs, comments=None) -> dict:
    """The fake gh's answers: the open PRs, their comments, and the overturn when off-due."""
    kwargs = {"prs": list(prs), "comments": dict(comments or {}), "all_prs": all_listed(prs)}
    if setting == "off-due":
        kwargs.update(all_issues=OFF_DUE, labels=list(ISSUE_LABELS))
    return kwargs


def one(setting: str, number: int) -> Case:
    """Status with one of the open PRs, and its comments."""
    found = [item for item in OPEN if item["number"] == number]
    return Case(steps(setting), fakes(setting, found, {number: RULED_COMMENTS.get(number, [])}))


CASES = {
    **{f"all, {name}": Case(steps(name), fakes(name, OPEN, RULED_COMMENTS)) for name in CONFIGS},
    "next, on, marked": one("on", 52),
    "next, on, sampled": one("on", 53),
    "next, on, first": one("on", 51),
    "next, false, marked": one("false", 52),
    "next, off-due": one("off-due", 53),
    "stage, on, first": Case(steps("on")),
    "stage, on, later": Case(steps("on", *stages(F2, 6), answer_step())),
    "stage, on, sampled": Case(steps("on", *stages(F2, 6), answer_step(), *stages(F3, 6))),
    "stage, false, later": Case(steps("false", *stages(F2, 6), answer_step())),
}
RULING = {51: [mark("engine", "ruling", 51, curl(51, 3))],
          52: [mark("engine", "ruling", 52, curl(52, 3))]}


class MergeCase(SpotCase):
    """Runs every case once, side by side."""

    @classmethod
    def setUpClass(cls):
        """Runs status once per case."""
        if not MergeCase.outs:
            MergeCase.outs = run_cases(CASES)

    def column(self, name: str, key: str) -> list:
        """``(number, value)`` of one key of every open PR, ``"missing"`` without it."""
        return [(p["number"], p.get(key, "missing")) for p in self.report(name)["open_prs"]]


class OpenPrTests(MergeCase):
    """``open_prs[].merged_by``, ``spot``, and ``risky`` in each setting (contract 5)."""

    def test_merged_by_without_spot_keys(self):
        """No ``spot_checks`` key: today's ``merged_by``, Troy for the first features only."""
        self.assertEqual(self.column("all, no keys", "merged_by"),
                         [(51, "troy"), (52, "f07"), (53, "f07"), (54, "f07"), (55, "f07"),
                          (56, "f07")])

    def test_merged_by_while_false(self):
        """``spot_checks = false``: the same, a marked PR of a later feature merged by F07."""
        self.assertEqual(self.column("all, false", "merged_by"),
                         [(51, "troy"), (52, "f07"), (53, "f07"), (54, "f07"), (55, "f07"),
                          (56, "f07")])

    def test_merged_by_while_on(self):
        """Planted bug "a risky PR merged": on, F03's marked PR 1 is Troy's; F04's sampled PR 1
        and F05's PR 2, unmarked, are F07's; PR 3 and a ``[docs]`` PR keep F07."""
        self.assertEqual(self.column("all, on", "merged_by"),
                         [(51, "troy"), (52, "troy"), (53, "f07"), (54, "f07"), (55, "f07"),
                          (56, "f07")])

    def test_merged_by_while_off_due(self):
        """Planted bug "spot checks left on after an overturn": off-due, every later PR 1 and
        PR 2 is Troy's, marked or not; PR 3 and the ``[docs]`` PR keep F07."""
        self.assertEqual(self.column("all, off-due", "merged_by"),
                         [(51, "troy"), (52, "troy"), (53, "troy"), (54, "troy"), (55, "f07"),
                          (56, "f07")])

    def test_spot_of_each_open_pr(self):
        """``spot``: the feature's for a PR 1 or 2 while on, null otherwise."""
        self.assertEqual(self.column("all, on", "spot"),
                         [(51, None), (52, "none"), (53, "sample"), (54, "none"), (55, None),
                          (56, None)])
        for name in ("all, false", "all, off-due"):
            with self.subTest(setting=name):
                self.assertEqual(self.column(name, "spot"),
                                 [(n, None) for n in (51, 52, 53, 54, 55, 56)])

    def test_risky_in_every_setting(self):
        """``risky``: the marks of a PR 1 or 2, whether spot checks are on or not; ``[]`` for
        PR 3, the ``[docs]`` PR, and unmarked PRs."""
        for name in ("all, false", "all, on", "all, off-due"):
            with self.subTest(setting=name):
                self.assertEqual(self.column(name, "risky"),
                                 [(51, RULING[51]), (52, RULING[52]), (53, []), (54, []),
                                  (55, []), (56, [])])

    def test_features_spot(self):
        """``features[].spot`` while on: null for F01 and F02, ``sample`` for F04 and F06."""
        self.assertEqual(self.feature_spots("all, on"),
                         [("F01", None), ("F02", None), ("F03", "none"), ("F04", "sample"),
                          ("F05", "none"), ("F06", "sample")])
        self.assertEqual(self.feature_spots("all, off-due"),
                         [(f.id, None) for f in SIX])


class NextTests(MergeCase):
    """``next.merged_by``, ``next.spot``, and ``next.risky`` (contract 5)."""

    def pr_next(self, name: str, number: int, feature, **expected) -> None:
        """Asserts ``continue-pr`` of an open PR 1."""
        self.assert_next(self.report(name), action="continue-pr", pr=number, item=feature.id,
                         stage=1, task="IF1", title=feature.title(1), branch=feature.branch(1),
                         **expected)

    def test_marked_pr1_waits_for_troy(self):
        """Planted bug "a risky PR merged": on, F03's ruled PR 1: Troy merges."""
        self.pr_next("next, on, marked", 52, F3, merged_by="troy", rounds=3, ruling=PM7_MERGE,
                     spot="none", risky=RULING[52])

    def test_sampled_pr1_is_merged_by_f07(self):
        """On, F04's sampled PR 1 without marks: F07 merges, Troy reviews after."""
        self.pr_next("next, on, sampled", 53, F4, merged_by="f07", spot="sample", risky=[])

    def test_first_features_pr1_is_troys(self):
        """On, F02 is among the first two: Troy merges, ``spot`` is null, and its ruling's
        mark is still listed."""
        self.pr_next("next, on, first", 51, F2, merged_by="troy", rounds=3, ruling=PM7_MERGE,
                     spot=None, risky=RULING[51])

    def test_marked_pr1_while_false(self):
        """Off: the marked PR 1 of F03 is F07's, as today, with its marks still listed."""
        self.pr_next("next, false, marked", 52, F3, merged_by="f07", rounds=3, ruling=PM7_MERGE,
                     spot=None, risky=RULING[52])

    def test_off_due_pr_waits(self):
        """Planted bug "spot checks left on after an overturn": off-due, the open PR comes
        first and Troy merges it."""
        self.pr_next("next, off-due", 53, F4, merged_by="troy", spot=None, risky=[])

    def test_stage_entries(self):
        """A stage 1 entry: F02's is Troy's; F03's is F07's (``none``); F04's is F07's
        (``sample``); with spot checks off, F03's is F07's with ``spot`` null."""
        for name, feature, merged_by, spot in (("stage, on, first", F2, "troy", None),
                                               ("stage, on, later", F3, "f07", "none"),
                                               ("stage, on, sampled", F4, "f07", "sample"),
                                               ("stage, false, later", F3, "f07", None)):
            with self.subTest(case=name):
                self.assert_next(self.report(name), action="stage", item=feature.id, stage=1,
                                 task="IF1", title=feature.title(1), branch=feature.branch(1),
                                 merged_by=merged_by, spot=spot, risky=[])


if __name__ == "__main__":
    unittest.main()
