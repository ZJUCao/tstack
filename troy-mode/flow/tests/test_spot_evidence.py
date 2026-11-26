"""The evidence for spot checks, E1 to E3 (F18 design 7.3, 13.1 "Spot checks"; contract 6).

``status`` gives ``spot_evidence`` at ``ask-approvals`` or with ``--spot-evidence``, else null:
E1, Troy's last 6 approvals of PR 1 and PR 2 changed nothing; E2, no ``requirement`` line in
TM8's real-run rulings of the last version with an accepted feature; E3, each case of the
roles behind PR 1 and PR 2 passed at least 4 of its newest 5 runs on the plugin's current
instructions, read from the role exam's case logs under ``TROY_EXAM_ROOT``. ``met`` is true
only when all three hold.

Planted bugs of design 13.2 caught here:

- "E3 read as passing without the case logs": ``EvidenceTests.test_unknown_without_evidence``
  and ``test_empty_case_folder_fails``.
- "E1 reading a changed PR as unchanged": ``EvidenceTests.test_e1_fails_on_a_changed_pr``.
- "E2 missing a ``requirement`` line": ``EvidenceTests.test_e2_fails_on_a_requirement``.
- "E3 counting a run of other instructions or a ``void`` run":
  ``EvidenceTests.test_e3_counts_only_matching_runs``.
"""

import unittest

from flow_helpers import Fakes, Project, base_step, new_dir, stages
from spot_helpers import (
    DEFAULT_ROOT, EVIDENCE_CASES, IF, WAIT_W3, Case, SpotCase, all_listed, answer_step,
    arch_review, at_minute, attempts, case_version, chain, env_root, expected_hash, flow,
    log_row, run_cases, run_without, spot_files, spot_module, stage_numbers, thread, tm_ruling,
    write_logs,
)
from stops_helpers import MERGE_FINDINGS, ruling

FOUR = chain(4, {1: "v0.1", 2: "v0.2", 3: "v0.2", 4: "v0.3"})
F1, F2, F3, F4 = FOUR
STEPS = [base_step(spot_files(FOUR, flow(1))), *stages(F1, 6), answer_step(), *stages(F2, 6),
         *stages(F3, 2), *stages(F4, 2)]
NONE_ACCEPTED = [base_step(spot_files(FOUR, flow(1))), *stages(F1, 2), *stages(F2, 2)]
CANDIDATES = (42, 41, 32, 31, 22, 21, 12, 11)
WAITED = (arch_review(1), WAIT_W3, "全按推荐")
NOT_WAITED = (arch_review(1),)
REVIEW_BEFORE = (arch_review(1, "changes-requested"), arch_review(2), WAIT_W3,
                 "Change the name, please.")
BY_ATTEMPT = (WAIT_W3, *attempts(IF, 1))
BY_REVIEW = (arch_review(1, "changes-requested"), WAIT_W3, "Please rename it.",
             arch_review(2, "approved"))
BY_RULING = (WAIT_W3, ruling("Product Manager", "merge", *MERGE_FINDINGS))
REQUIREMENT = tm_ruling(("bug", "the total is off by one"),
                        ("requirement", "Troy wants a total per folder"))
NO_REQUIREMENT = tm_ruling(("bug", "the total is off by one"), ("prototype", "the help text"),
                           ("later F04", "watch folders"), ("setup", "the PATH lacks wc"),
                           ("console", "the code page"))
OTHER_PRS = [(13, F1.title(3)), (16, F1.title(6)), (26, F2.title(6)), (70, "[docs] Release v0.1.0"),
             (75, "[docs] Release v0.2.0"), (85, "[docs] Release v0.2.1")]


def listed_prs() -> list:
    """Every PR: the stage 1 and 2 PRs of F01 to F04, F01's mock, both accepts, three
    releases, and F03's accept closed without merging."""
    merged = [*stage_numbers(F1, 2, 10), *stage_numbers(F2, 2, 20), *stage_numbers(F3, 2, 30),
              *stage_numbers(F4, 2, 40), *OTHER_PRS]
    found = all_listed((), merged)
    found.append({"number": 36, "title": F3.title(6), "state": "CLOSED",
                  "url": "https://github.com/ZJUCao/wordcount/pull/36",
                  "createdAt": "2026-11-10T08:00:00Z"})
    return found


def comments_of(e1: dict, e2: dict) -> dict:
    """PR number mapped to its comments: ``e1`` for the candidates (``WAITED`` by default),
    ``e2`` for the acceptance and release PRs."""
    found = {number: thread(number, *e1.get(number, WAITED)) for number in CANDIDATES}
    found[13] = thread(13, *WAITED)
    for number in (16, 26, 36, 70, 75, 85):
        found[number] = thread(number, *e2.get(number, ()))
    return found


E1_HOLDS = {42: NOT_WAITED, 22: REVIEW_BEFORE, 11: BY_ATTEMPT}
E1_FAILS = {42: NOT_WAITED, 41: BY_ATTEMPT, 31: BY_REVIEW, 21: BY_RULING}
E1_UNKNOWN = {42: NOT_WAITED, 41: NOT_WAITED, 32: NOT_WAITED}
E2_FAILS = {16: (REQUIREMENT,), 26: (REQUIREMENT,), 36: (REQUIREMENT,), 70: (REQUIREMENT,),
            75: (NO_REQUIREMENT,), 85: (REQUIREMENT,)}
E2_HOLDS = {16: (REQUIREMENT,), 26: (NO_REQUIREMENT,), 70: (REQUIREMENT,),
            85: ("1. requirement: a comment that is no ruling",)}


def logs_holding(digest: str) -> dict:
    """Every case: five runs on these instructions, four of them passed."""
    return {case: [log_row(at_minute(i), i != 0, digest, case_version(case)) for i in range(5)]
            for case in EVIDENCE_CASES}


def logs_mixed(digest: str) -> dict:
    """One case holds, one fails on its newest 5 though its file's last 5 pass, one fails,
    one has 4 matching runs among others, and one has no log."""
    version = {case: case_version(case) for case in EVIDENCE_CASES}
    passes = {1: True, 2: False, 3: True, 4: True, 5: True, 6: False}   # minute: passed
    error_rules = [log_row(at_minute(m), passes[m], digest, version["if-error-rules"])
                   for m in (6, 1, 3, 2, 5, 4)]
    ar_error = [log_row(at_minute(m), True, digest, version["ar-error-review"])
                for m in (1, 2, 3, 4)]
    ar_error += [log_row(at_minute(5), True, "0" * 64, version["ar-error-review"]),
                 log_row(at_minute(6), True, digest, version["ar-error-review"], "void"),
                 log_row(at_minute(7), True, digest, version["ar-error-review"] + 1)]
    return {
        "if-example-format": [log_row(at_minute(m), True, digest, version["if-example-format"])
                              for m in range(5)],
        "if-error-rules": error_rules,
        "ar-design-review": [log_row(at_minute(m), m < 3, digest, version["ar-design-review"])
                             for m in range(5)],
        "ar-error-review": ar_error,
    }


def entry(case: str, result: str, runs: int, passed: int) -> dict:
    """One case of E3."""
    return {"id": case, "result": result, "runs": runs, "passed": passed}


class EvidenceTests(SpotCase):
    """``spot_evidence`` with ``--spot-evidence`` (contract 6)."""

    @classmethod
    def setUpClass(cls):
        """Writes the case logs and runs status once per case, side by side."""
        cls.digest = expected_hash()
        cls.roots = {"holds": write_logs(new_dir("examroot"), logs_holding(cls.digest)),
                     "mixed": write_logs(new_dir("examroot"), logs_mixed(cls.digest)),
                     "no cases": new_dir("examroot"), "empty": write_logs(new_dir("examroot"),
                                                                          {})}
        flag = ("--spot-evidence",)
        prs = listed_prs()
        cases = {
            "holds": Case(STEPS, {"all_prs": prs, "comments": comments_of(E1_HOLDS, E2_HOLDS)},
                          flag, env=env_root(cls.roots["holds"])),
            "fails": Case(STEPS, {"all_prs": prs, "comments": comments_of(E1_FAILS, E2_FAILS)},
                          flag, env=env_root(cls.roots["mixed"])),
            "unknown": Case(NONE_ACCEPTED, {"all_prs": prs,
                                            "comments": comments_of(E1_UNKNOWN, {})},
                            flag, env=env_root(cls.roots["no cases"])),
            "empty": Case(STEPS, {"all_prs": prs, "comments": comments_of(E1_HOLDS, E2_HOLDS)},
                          flag, env=env_root(cls.roots["empty"])),
            "no flag": Case(STEPS, {"all_prs": prs, "comments": comments_of(E1_HOLDS, E2_HOLDS)},
                            env=env_root(cls.roots["holds"])),
        }
        cls.outs = run_cases(cases)

    def evidence(self, name: str):
        """The case's ``spot_evidence``, which must be present."""
        report = self.report(name)
        self.assertTrue("spot_evidence" in report, f"no 'spot_evidence': {sorted(report)}")
        return report["spot_evidence"]

    def part(self, name: str, key: str):
        """One of E1, E2, E3 of the case's evidence."""
        evidence = self.evidence(name)
        self.assertIsInstance(evidence, dict, evidence)
        return evidence.get(key, "missing")

    def test_all_three_hold(self):
        """Six unchanged approvals, no ``requirement`` line, every case at 4 of 5: met."""
        self.assertEqual(self.evidence("holds"), {
            "met": True,
            "E1": {"result": "holds", "prs": [41, 32, 31, 22, 21, 12], "changed": []},
            "E2": {"result": "holds", "version": "v0.2", "requirement": []},
            "E3": {"result": "holds", "root": str(self.roots["holds"]),
                   "instructions": self.digest,
                   "cases": [entry(case, "holds", 5, 4) for case in EVIDENCE_CASES]}})

    def test_e1_skips_prs_that_did_not_wait(self):
        """#42 merged without waiting and #13 is a mock: neither is counted; #11 changed but is
        the seventh; a review before the wait and Troy's words after it change nothing."""
        self.assertEqual(self.part("holds", "E1")["prs"], [41, 32, 31, 22, 21, 12])

    def test_e1_fails_on_a_changed_pr(self):
        """Planted bug "E1 reading a changed PR as unchanged": an attempt, a review, and a
        ruling after the wait: changed, highest number first."""
        self.assertEqual(self.part("fails", "E1"),
                         {"result": "fails", "prs": [41, 32, 31, 22, 21, 12],
                          "changed": [41, 31, 21]})

    def test_e2_fails_on_a_requirement(self):
        """Planted bug "E2 missing a ``requirement`` line": v0.2's accept #26 and release #85
        have one; v0.1's PRs and the closed #36 do not count."""
        self.assertEqual(self.part("fails", "E2"),
                         {"result": "fails", "version": "v0.2", "requirement": [26, 85]})

    def test_e3_counts_only_matching_runs(self):
        """Planted bug "E3 counting a run of other instructions or a void run": the newest 5
        by time, on this hash and case version, not void."""
        self.assertEqual(self.part("fails", "E3"), {
            "result": "fails", "root": str(self.roots["mixed"]), "instructions": self.digest,
            "cases": [entry("if-example-format", "holds", 5, 5),
                      entry("if-error-rules", "fails", 6, 3),
                      entry("ar-design-review", "fails", 5, 3),
                      entry("ar-error-review", "no runs", 4, 4),
                      entry("tm-plan-expected", "no runs", 0, 0)]})
        self.assertIs(self.evidence("fails")["met"], False)

    def test_unknown_without_evidence(self):
        """Planted bug "E3 read as passing without the case logs": fewer than 6 waits, no
        accepted feature, and no ``cases`` folder: each unknown, not met."""
        self.assertEqual(self.evidence("unknown"), {
            "met": False,
            "E1": {"result": "unknown", "prs": [31, 22, 21, 12, 11], "changed": []},
            "E2": {"result": "unknown", "version": None, "requirement": []},
            "E3": {"result": "unknown", "root": str(self.roots["no cases"]),
                   "instructions": self.digest, "cases": []}})

    def test_empty_case_folder_fails(self):
        """Planted bug "E3 read as passing without the case logs": a ``cases`` folder without
        logs: every case has no runs, E3 fails, not met."""
        self.assertEqual(self.part("empty", "E3"), {
            "result": "fails", "root": str(self.roots["empty"]), "instructions": self.digest,
            "cases": [entry(case, "no runs", 0, 0) for case in EVIDENCE_CASES]})
        self.assertIs(self.evidence("empty")["met"], False)

    def test_null_without_the_flag(self):
        """No ``--spot-evidence`` and no ``ask-approvals``: the key is there, null."""
        self.assertIsNone(self.evidence("no flag"))


class AskApprovalsTests(SpotCase):
    """At ``ask-approvals`` the evidence comes without the flag (contract 6; design 7.4)."""

    @classmethod
    def setUpClass(cls):
        """F01 accepted, the one feature Troy approves, and no answer yet."""
        three = chain(3)
        prs = all_listed((), [(11, three[0].title(1)), (12, three[0].title(2)),
                              (16, three[0].title(6))])
        comments = {11: thread(11, *WAITED), 12: thread(12, *WAITED), 16: thread(16)}
        cls.root = new_dir("examroot")
        cls.outs = run_cases({"ask": Case(
            [base_step(spot_files(three, flow(1))), *stages(three[0], 6)],
            {"all_prs": prs, "comments": comments}, env=env_root(cls.root))})

    def test_evidence_at_ask_approvals(self):
        """``next`` is ``ask-approvals``, and ``spot_evidence`` holds E1 to E3."""
        report = self.report("ask")
        self.assertEqual(report["next"]["action"], "ask-approvals")
        self.assertEqual(report.get("spot_evidence", "missing"), {
            "met": False,
            "E1": {"result": "unknown", "prs": [12, 11], "changed": []},
            "E2": {"result": "holds", "version": "v0.1", "requirement": []},
            "E3": {"result": "unknown", "root": str(self.root), "instructions": expected_hash(),
                   "cases": []}})


class RootAndHashTests(SpotCase):
    """E3's default root and the plugin's instruction hash (contract 6 and 9)."""

    def test_default_root(self):
        """Without ``TROY_EXAM_ROOT``: ``D:\\Troy\\troy-mode-work``, with the plugin's hash."""
        project = Project([base_step(spot_files(chain(3), flow(1)))])
        out = run_without(project, ["status", "--spot-evidence"], Fakes(), "TROY_EXAM_ROOT")
        report = self.report_of(out, 0, "status")
        e3 = (report.get("spot_evidence") or {}).get("E3") or {}
        self.assertEqual((e3.get("root"), e3.get("instructions")), (DEFAULT_ROOT, expected_hash()))

    def test_plugin_hash_is_the_exams(self):
        """``troyflow.spot.plugin_hash()`` is ``instruction_hash(FolderTree(<plugin root>))``."""
        try:
            spot = spot_module()
        except AssertionError as exc:
            self.fail(str(exc))
        self.assertEqual(spot.plugin_hash(), expected_hash())


if __name__ == "__main__":
    unittest.main()
