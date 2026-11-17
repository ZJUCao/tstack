"""Labels and text (F15 design 8, 9; 13.1 "Labels and text"; interface note sections 1 and 4).

The labels ``issues`` asks the main session to create, both languages with
the boxes once, no time stamp, full URLs, the size limit, duplicates,
repositories with issues turned off, the order of actions, and gh failures.

Planted bugs of design 13.2 caught here:

- "a missing label used before it exists": ``LabelTests.test_missing_labels_get_create_commands``
  and ``test_only_the_missing_ones``.
- "an existing label changed": ``LabelTests.test_existing_labels_are_never_changed``.
- "the size limit counted in bytes": ``SizeTests.test_limit_counts_characters_not_bytes``.
- "the newer duplicate kept": ``DuplicateTests.test_newer_duplicate_is_closed``.
"""

import unittest
from dataclasses import replace

from flow_helpers import ALL_ISSUES_ARGS, ALL_PRS_ARGS, F01, F03, base_step, stages
from issues_helpers import (
    ALL_LABELS, BLOB, COMMIT1, EN_PERF, EN_SCENARIOS, LABELS, RELEASE_FEATURES, TAG, ZH_PERF,
    ZH_SCENARIOS, IssuesCase, box_lines, checklist_marker, issues_runs, lines_of,
    passed, plan_pair, progress_issue, progress_marker, project_files, release_fakes,
    release_steps, split_body, stage_prs, waiting,
)

DISABLED = "the 'ZJUCao/wordcount' repository has disabled issues"
BAD_GATEWAY = "HTTP 502: Bad Gateway (https://api.github.com/graphql)"
F03V2 = replace(F03, version="v0.2")
BIG_ZH = "步" * 31000
BIG_EN = "step " * 6000
WIDE_ZH = "步" * 25000


def with_steps(zh_steps: str, en_steps: str) -> dict:
    """The plan pair with v0.1-S02's steps replaced in both languages."""
    def swap(rows, steps):
        """Rows with S02's Steps cell replaced."""
        return [(*row[:3], steps, row[4]) if row[0] == "v0.1-S02" else row for row in rows]
    return plan_pair(scenarios=(swap(EN_SCENARIOS, en_steps), swap(ZH_SCENARIOS, zh_steps)),
                     perf=(EN_PERF, ZH_PERF))


def base():
    """The first commit, with a Chinese mirror that has a features table."""
    return base_step(project_files())


def release_open() -> dict:
    """Fakes for release PR #30 with run 1 passed."""
    return release_fakes(passed(1, COMMIT1), waiting())


CASES = {
    "no labels": ([base()], {"labels": ["bug"]}),
    "progress only": ([base()], {"labels": ["bug", "progress"]}),
    "all labels": ([base()], {"labels": list(ALL_LABELS)}),
    "turned off": ([base()], {"labels": ["bug"], "issues_enabled": False}),
    "disabled text": ([base()], {"labels": ["bug"], "fail_on": [
        (["issue", "list", "--state", "all"], DISABLED)]}),
    "repo view fails": ([base()], {"fail_on": [(["repo", "view"], BAD_GATEWAY)]}),
    "label list fails": ([base()], {"fail_on": [(["label", "list"], BAD_GATEWAY)]}),
    "issue list fails": ([base()], {"fail_on": [(["issue", "list", "--state", "all"],
                                                 BAD_GATEWAY)]}),
    "PR list fails": ([base()], {"fail_on": [(["pr", "list", "--state", "all"], BAD_GATEWAY)]}),
    "every call fails": ([base()], {"fail": True}),
    "duplicates": ([base()], {"labels": list(ALL_LABELS), "all_issues": [
        progress_issue(12, "F01"), progress_issue(7, "F01"),
        progress_issue(15, "F01", state="CLOSED", reason="NOT_PLANNED")]}),
    "progress": ([base(), *stages(F01, 2)], {"labels": list(ALL_LABELS),
                                              "all_prs": stage_prs(F01, 2)}),
    "checklist": (release_steps(), release_open()),
    "two kinds": (release_steps(features=(*RELEASE_FEATURES, F03V2)), release_open()),
    "big": (release_steps(with_steps(BIG_ZH, BIG_EN)), release_open()),
    "wide": (release_steps(with_steps(WIDE_ZH, "Open a terminal and run wc notes.txt")),
             release_open()),
}


class TextCase(IssuesCase):
    """Runs every case once, side by side."""

    outs: dict = {}

    @classmethod
    def setUpClass(cls):
        """Runs ``issues`` on one clone per case."""
        if not TextCase.outs:
            TextCase.outs = issues_runs(CASES)

    def report(self, name: str) -> dict:
        """A case's report; the run must exit 0 and only read GitHub."""
        out, fake, _ = self.outs[name]
        self.assert_read_only(fake)
        return self.issues_report(out)

    def body(self, name: str, kind: str) -> str:
        """The body of the case's one create action of a kind."""
        found = [a for a in self.report(name)["actions"]
                 if a["kind"] == kind and a["action"] == "create"]
        self.assertEqual(len(found), 1, self.report(name)["actions"])
        return self.body_of(found[0])


class LabelTests(TextCase):
    """The labels of design 8.1 (note 4.3)."""

    def expected(self, *names: str) -> list:
        """The report's label entries for the named labels, in the note's order."""
        entries = []
        for name, color, description in LABELS:
            if name in names:
                argv = ["label", "create", name, "--color", color, "--description", description]
                entries.append({"name": name, "color": color, "description": description,
                                "argv": argv})
        return entries

    def labels(self, name: str) -> list:
        """A case's label entries, each command checked, without the command."""
        entries = self.report(name)["labels"]
        for entry in entries:
            self.assert_command(entry)
        return [{k: v for k, v in entry.items() if k != "command"} for entry in entries]

    def test_missing_labels_get_create_commands(self):
        """Planted bug "a missing label used before it exists": all three, in order, exact."""
        self.assertEqual(self.labels("no labels"), self.expected("idea", "progress",
                                                                 "device-test"))
        self.assertEqual(self.report("no labels")["actions"][0]["labels"], ["progress"])

    def test_only_the_missing_ones(self):
        """``progress`` exists: only ``idea`` and ``device-test``."""
        self.assertEqual(self.labels("progress only"), self.expected("idea", "device-test"))

    def test_existing_labels_are_never_changed(self):
        """Planted bug "an existing label changed": all exist, no entry and no label write."""
        report = self.report("all labels")
        self.assertEqual(report["labels"], [])
        words = [entry["argv"][:2] for entry in report["actions"]]
        self.assertNotIn(["label", "edit"], words)
        self.assertNotIn(["label", "create"], words)

    def test_repository_url(self):
        """``repository`` is ``gh repo view``'s URL."""
        self.assertEqual(self.report("all labels")["repository"],
                         "https://github.com/ZJUCao/wordcount")


class TurnedOffTests(TextCase):
    """A repository with issues turned off (design 9; note section 1)."""

    def test_issues_turned_off_are_skipped(self):
        """``hasIssuesEnabled`` false, or GitHub's "disabled issues": exit 0, nothing to do."""
        for name in ("turned off", "disabled text"):
            with self.subTest(case=name):
                report = self.report(name)
                self.assertEqual((report["skipped"], report["labels"], report["actions"]),
                                 (["issues are turned off"], [], []))

    def test_issues_on_are_not_skipped(self):
        """Pair: issues on, the same state: no skip, F01's issue and the labels."""
        report = self.report("no labels")
        self.assertEqual(report["skipped"], [])
        self.assertEqual([(a["action"], a["item"]) for a in report["actions"]],
                         [("create", "F01")])

    def test_failed_reads_exit_two(self):
        """A failing ``repo view``, ``label list``, ``issue list``, or ``pr list``: exit 2."""
        failing = {"repo view fails": ["repo", "view"], "label list fails": ["label", "list"],
                   "issue list fails": ALL_ISSUES_ARGS[:4], "PR list fails": ALL_PRS_ARGS[:4],
                   "every call fails": None}
        for name, words in failing.items():
            with self.subTest(case=name):
                self.assert_exit(self.outs[name][0], 2)
                calls = self.outs[name][1].gh_argvs()
                self.assert_read_only(self.outs[name][1])
                if words is None:
                    self.assertNotEqual(calls, [], "the engine asked gh nothing")
                else:
                    self.assertIn(words, [argv[:len(words)] for argv in calls],
                                  f"the failing call was never made: {calls}")


class DuplicateTests(TextCase):
    """Two issues for one feature (design 9; note section 4)."""

    def test_newer_duplicate_is_closed(self):
        """Planted bug "the newer duplicate kept": #12 closed as a duplicate of #7, first;
        #7 is rebuilt; the closed #15 is left alone."""
        actions = self.report("duplicates")["actions"]
        self.assertEqual([(a["action"], a["number"]) for a in actions],
                         [("close-duplicate", 12), ("edit", 7)])
        self.assert_duplicate(actions[0], "progress", "F01", 12, 7)
        self.assert_edit(actions[1], self.outs["duplicates"][2], "progress", "F01", 7,
                         "F01 数单词 / Count words")


class ShapeTests(TextCase):
    """Both languages, Chinese first, the boxes once, no stamp, full URLs (design 8.2, 8.3)."""

    def test_progress_body_shape(self):
        """A progress body with links to the design and the test plan."""
        body = self.body("progress", "progress")
        self.assert_body_shape(body, progress_marker("F01"))
        chinese, english = split_body(body)
        self.assertEqual(len(box_lines(chinese)), 6)
        self.assertGreaterEqual(body.count(BLOB), 6, body)

    def test_checklist_body_shape(self):
        """A checklist body with its links."""
        body = self.body("checklist", "device-test")
        self.assert_body_shape(body, checklist_marker(TAG))
        self.assertGreaterEqual(body.count(BLOB), 4, body)

    def test_no_relative_links(self):
        """No link to a relative path, in either body."""
        for name, kind in (("progress", "progress"), ("checklist", "device-test")):
            with self.subTest(body=name):
                body = self.body(name, kind)
                for fragment in ("](docs/", "](../", "](./", "](/"):
                    self.assertNotIn(fragment, body)

    def test_progress_actions_before_checklist_actions(self):
        """F03 of v0.2 is next during v0.1's release: its issue first, then the checklist."""
        actions = self.report("two kinds")["actions"]
        self.assertEqual([(a["action"], a["kind"], a["item"]) for a in actions],
                         [("create", "progress", "F03"), ("create", "device-test", TAG)])


class SizeTests(TextCase):
    """Bodies stay under 60,000 characters (design 8.3; note 4.2)."""

    def test_long_steps_are_shortened_with_a_problem(self):
        """Steps that would pass 60,000 characters become links; one problem names the tag."""
        report = self.report("big")
        body = self.body("big", "device-test")
        self.assertLessEqual(len(body), 60000)
        self.assertNotIn("步" * 100, body)
        self.assertNotIn("step step step", body)
        self.assertEqual(len(report["problems"]), 1, report["problems"])
        self.assertIn(TAG, str(report["problems"][0]))
        chinese, english = split_body(body)
        steps = [line for line in chinese if line.startswith("  步骤：")]
        self.assertEqual(len(steps), 3, chinese)
        for line in steps:
            with self.subTest(line=line):
                self.assertTrue(line.startswith(f"  步骤：见[版本测试方案]({BLOB}docs/versions/"
                                                "v0.1/test-plan"), line)
        self.assertIn("  预期：显示统计结果", chinese)
        self.assertIn("- [ ] **v0.1-S02 在 Troy 的笔记本上统计**", chinese)
        self.assertTrue([line for line in english
                         if f"Steps: see [the version test plan]({BLOB}docs/versions/v0.1/"
                         "test-plan" in line], english)
        self.assertEqual(self.outs["big"][0].code, 0)

    def test_limit_counts_characters_not_bytes(self):
        """Planted bug "counted in bytes": 25,000 Chinese characters (75,000 bytes) stay."""
        report = self.report("wide")
        body = self.body("wide", "device-test")
        self.assertGreater(len(body.encode("utf-8")), 60000)
        self.assertLess(len(body), 60000)
        self.assertIn("  步骤：" + WIDE_ZH, lines_of(body))
        self.assertEqual(report["problems"], [])


if __name__ == "__main__":
    unittest.main()
