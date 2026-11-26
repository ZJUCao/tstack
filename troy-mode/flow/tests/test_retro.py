"""retro (F08 design 3.1, 7, D76, 11.1; interface note sections 1, 2, and 11).

One history with two versions and a patch between them: v0.1.0 (PR #11),
v0.1.1 (PR #14), and v0.2.0 (PR #24). ``retro --tag v0.2.0`` reads the PRs
after v0.1.0's release commit, a version's and not the patch's, up to
v0.2.0's; ``retro --tag v0.1.0`` reads from the first commit.

Planted bugs of F08 design 11.2 caught here:

- "``retro`` reading PRs from before the previous tag":
  ``RetroTests.test_prs_since_the_previous_version`` and
  ``test_findings_before_the_previous_tag_do_not_count``.
- "a finding seen once counted as repeated": ``RetroTests.test_groups_in_order`` and
  ``test_repeated_lists_only_groups_seen_in_two_prs`` (a finding twice in one PR, once
  elsewhere).
"""

import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from flow_helpers import (
    F01, F02, LOGIN, PROJECT, SCRATCH, Fakes, FlowCase, Project, accepted_plan_files,
    base_files, base_step, bug_step, comments, commit_time, hooks_line, issue, merged_pr,
    new_dir, parallel, run_engine, stages, step, subject_commits, version_tests_step,
    release_step, write_file,
)

MERGED_ARGS = ["pr", "list", "--state", "merged", "--limit", "200", "--json",
               "number,title,url,mergeCommit,headRefName,createdAt,mergedAt"]
F02V2 = replace(F02, version="v0.2")
CR = "Code Reviewer review, round 1: changes-requested"
TM = "Test Manager review, round 1: changes-requested"
ESCALATION = "Escalation: three review rounds without agreement"
LONG = "The function returns the wrong value when the input is one very long line of text."

STEPS = ([base_step(base_files((F01, F02V2)))] + stages(F01, 6)
         + [bug_step("B4", "test", "Wrong count"), bug_step("B4", "fix", "Wrong count"),
            version_tests_step("v0.1"),
            release_step("v0.1.0", accepted_plan_files("v0.1", ["F01"], ["v0.1.0"])),
            bug_step("B13", "test", "Wrong count of tabs"),
            bug_step("B13", "fix", "Wrong count of tabs"),
            release_step("v0.1.1", accepted_plan_files("v0.1", ["F01"], ["v0.1.0", "v0.1.1"]),
                         tags=["v0.1.0", "v0.1.1"])]
         + stages(F02V2, 6)
         + [bug_step("B15", "test", "Crash when the file is empty"),
            bug_step("B15", "fix", "Crash when the file is empty"),
            version_tests_step("v0.2"),
            release_step("v0.2.0", accepted_plan_files("v0.2", ["F02"], ["v0.2.0"]),
                         tags=["v0.1.0", "v0.1.1", "v0.2.0"]),
            step("[docs] Explain the release in the README", {"README.md": "# wordcount\n\n"
                                                                            "Released.\n"})])
NUMBERS = {item.subject: number for number, item in enumerate(STEPS, start=1)}
NULL_MERGE_COMMIT = (5, 18)

COMMENTS = {
    4: comments(f"{CR}\n\n1. R05: src/wordcount/f01.py:3, add a doc comment.\n"
                "2. Docs: explain the return value."),
    6: comments(f"{CR}\n\n1. Docs: the module has no summary."),
    12: comments(f"{TM}\n\n1. Naming: the test name is vague.\n"
                 "2. Naming: the fixture name too."),
    17: comments(f"{CR}\n\n1. R05: src/wordcount/f02.py:3, add a doc comment.\n"
                 "2. R05: src/wordcount/f02.py:9, add a doc comment.\n"
                 "3. Naming: rename count() to count_lines().\n"
                 f"4. {LONG}",
                 "Please also check these:\n1. R07: the loop is too deep.\n2. R07: still too deep.",
                 "Developer attempt 1: failed\n\nruff check: 2 errors\n"
                 "R04: count_lines is too long."),
    18: comments(f"{TM}\n\n1. [blocking] Coverage: F02-T03 has no test.\n"
                 "2. (non-blocking) Coverage: F02-T04 could use a second case.",
                 "Test Manager review, round 2: approved\n\n1. R08: a minor note."),
    19: comments(f"{CR}\n\n1. R05: count_lines has no doc comment.\n"
                 "2) **Naming**: the helper name `tmp` is vague.\n"
                 "3. naming: the test file name.\n"
                 "4. `Error handling`: the empty file case raises.",
                 "Developer attempt 1: failed\n\nmypy: 1 error",
                 "Also:\n1. R07: and here."),
    20: comments(f"{ESCALATION}\n\nWhere it stopped: the reviewers disagree."),
    22: comments("Developer attempt 1: failed\n\nruff: 3 errors",
                 f"{CR}\n\n1. non-blocking: Error handling: say which file failed.\n"
                 "2. R05 again: the fix has no doc comment."),
    24: comments("Release test, run 1: failed\n\n1. R05: v0.2-S01 failed.",
                 "Accepted. Works on my laptop."),
}
ISSUES = {4: issue(4, "Words counted twice"), 13: issue(13, "Tabs are counted as words"),
          15: issue(15, "Crash on an empty file")}


def url(number: int) -> str:
    """A PR's URL."""
    return f"https://github.com/{LOGIN}/{PROJECT}/pull/{number}"


def stamp(seconds: int) -> str:
    """A hooks.log time, ``YYYY-MM-DDTHH:MM:SSZ``, in UTC."""
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RetroTests(FlowCase):
    """The evidence for v0.2.0's and v0.1.0's retrospectives (note section 11)."""

    @classmethod
    def setUpClass(cls):
        """One clone, its merged PRs and hooks.log, and retro for each tag, side by side."""
        cls.project = Project(STEPS)
        shas = subject_commits(cls.project)
        merged = []
        for item in STEPS:
            number = NUMBERS[item.subject]
            oid = None if number in NULL_MERGE_COMMIT else shas[item.subject]
            merged.append(merged_pr(number, item.subject, oid))
        merged.append(merged_pr(26, "[docs] Never on main", None))
        start = commit_time(cls.project, shas["[docs] Release v0.1.0"])
        lines = [hooks_line(stamp(start - 3600), None, None, "scope"),
                 hooks_line(stamp(start), "tstack:troy-developer", "a1", "scope"),
                 hooks_line(stamp(start + 120), "tstack:troy-developer", "a2", "scope"),
                 hooks_line(stamp(start + 180), None, None, "bash")]
        text = ("".join(json.dumps(line) + "\n" for line in lines[:2]) + "not json at all\n"
                + "".join(json.dumps(line) + "\n" for line in lines[2:]))
        write_file(cls.project.git_dir(), "troy-mode/hooks.log", text)
        cls.before = (cls.project.status_lines(), cls.project.head(),
                      (cls.project.git_dir() / "troy-mode/hooks.log").read_bytes())
        cls.fakes = {tag: Fakes(merged=merged, comments=COMMENTS, issue_views=ISSUES)
                     for tag in ("v0.2.0", "v0.1.0")}
        outs = parallel(lambda tag: cls.project.run("retro", "--tag", tag, fakes=cls.fakes[tag]),
                        ["v0.2.0", "v0.1.0"])
        cls.outs = dict(zip(["v0.2.0", "v0.1.0"], outs))

    def report(self, tag: str) -> dict:
        """The retro report of one tag, which must have exit code 0."""
        return self.report_of(self.outs[tag], 0, "retro")

    def group(self, tag: str, key: str) -> dict:
        """One group of a report, by key."""
        found = [g for g in self.report(tag)["groups"] if g["key"] == key]
        self.assertEqual(len(found), 1, [g["key"] for g in self.report(tag)["groups"]])
        return found[0]

    def test_prs_since_the_previous_version(self):
        """Planted bug "PRs from before the previous tag": #12 to #24, after v0.1.0 (not
        v0.1.1), with #18's null merge commit matched by its title."""
        report = self.report("v0.2.0")
        self.assertEqual((report["tag"], report["previous"]), ("v0.2.0", "v0.1.0"))
        self.assertEqual([p["number"] for p in report["prs"]], list(range(12, 25)))
        first = report["prs"][0]
        self.assertEqual(first, {"number": 12, "title": "[B13 A/B test] Wrong count of tabs",
                                 "url": url(12)})

    def test_first_version_reads_from_the_first_commit(self):
        """v0.1.0 has no previous version: #1 to #11, #5's null merge commit included."""
        report = self.report("v0.1.0")
        self.assertIsNone(report["previous"])
        self.assertEqual([p["number"] for p in report["prs"]], list(range(1, 12)))

    def test_groups_in_order(self):
        """Every group's key, kind, PRs, count, and repeated flag, in the note's order."""
        found = [(g["key"], g["kind"], g["prs"], g["count"], g["repeated"])
                 for g in self.report("v0.2.0")["groups"]]
        self.assertEqual(found, [
            ("naming", "item", [12, 17, 19], 5, True),
            ("R05", "rule", [17, 19, 22], 4, True),
            ("Developer attempt failed", "attempt", [19, 22], 2, True),
            ("error handling", "item", [19, 22], 2, True),
            ("hooks.log: scope", "hooks", [], 2, True),
            ("coverage", "item", [18], 2, False),
            (ESCALATION, "escalation", [20], 1, False),
            ("R04", "rule", [17], 1, False),
            ("hooks.log: bash", "hooks", [], 1, False),
        ])

    def test_repeated_lists_only_groups_seen_in_two_prs(self):
        """Planted bug "a finding seen once counted as repeated": coverage twice in #18 only."""
        report = self.report("v0.2.0")
        self.assertEqual(report["repeated"], ["naming", "R05", "Developer attempt failed",
                                              "error handling", "hooks.log: scope"])

    def test_troys_comments_and_approved_reviews_do_not_count(self):
        """R07 is only in Troy's comments and R08 only in an approved review: no group."""
        keys = {g["key"] for g in self.report("v0.2.0")["groups"]}
        self.assertNotIn("R07", keys)
        self.assertNotIn("R08", keys)

    def test_findings_before_the_previous_tag_do_not_count(self):
        """Planted bug "PRs from before the previous tag": #4's and #6's findings stay out."""
        keys = {g["key"] for g in self.report("v0.2.0")["groups"]}
        self.assertNotIn("docs", keys)
        self.assertNotIn(4, self.group("v0.2.0", "R05")["prs"])

    def test_evidence_names_the_pr_heading_and_text(self):
        """R05's evidence: four findings, each with its PR, URL, review heading, and text."""
        evidence = sorted((e["pr"], e["url"], e["heading"], e["text"])
                          for e in self.group("v0.2.0", "R05")["evidence"])
        self.assertEqual(evidence, [
            (17, url(17), CR, "R05: src/wordcount/f02.py:3, add a doc comment."),
            (17, url(17), CR, "R05: src/wordcount/f02.py:9, add a doc comment."),
            (19, url(19), CR, "R05: count_lines has no doc comment."),
            (22, url(22), CR, "R05 again: the fix has no doc comment.")])

    def test_finding_without_a_key_is_ungrouped(self):
        """A long sentence with no rule ID and no short item before a colon."""
        self.assertEqual(self.report("v0.2.0")["ungrouped"],
                         [{"pr": 17, "heading": CR, "text": LONG}])

    def test_bugs_fixed_in_the_range(self):
        """B13 and B15, with their summaries and the issues' titles and URLs."""
        bugs = sorted(self.report("v0.2.0")["bugs"], key=lambda b: b["issue"])
        self.assertEqual(bugs, [
            {"id": "B13", "issue": 13, "summary": "Wrong count of tabs",
             "title": "Tabs are counted as words", "url": ISSUES[13]["url"]},
            {"id": "B15", "issue": 15, "summary": "Crash when the file is empty",
             "title": "Crash on an empty file", "url": ISSUES[15]["url"]}])

    def test_first_version_groups_and_bugs(self):
        """v0.1.0: docs in #4 and #6 repeats, R05 once; every hooks.log line counts; B4."""
        report = self.report("v0.1.0")
        found = {g["key"]: (g["prs"], g["count"], g["repeated"]) for g in report["groups"]}
        self.assertEqual(found["docs"], ([4, 6], 2, True))
        self.assertEqual(found["R05"], ([4], 1, False))
        self.assertEqual(found["hooks.log: scope"], ([], 3, True))
        self.assertEqual(report["repeated"], ["docs", "hooks.log: scope"])
        self.assertEqual([b["id"] for b in report["bugs"]], ["B4"])

    def test_gh_calls_and_nothing_changed(self):
        """The merged PR list, each PR's comments, each fixed bug's issue, and one list of CI
        runs (F07 D261); no file changes."""
        self.report("v0.2.0")
        calls = self.fakes["v0.2.0"].gh_argvs()
        self.assertIn(MERGED_ARGS, calls)
        views = sorted(int(c[2]) for c in calls if c[:2] == ["pr", "view"])
        self.assertEqual(views, list(range(12, 25)))
        self.assertEqual(sorted(c[2] for c in calls if c[:2] == ["issue", "view"]), ["13", "15"])
        self.assertEqual(sum(1 for c in calls if c[:2] == ["run", "list"]), 1)
        for argv in calls:
            with self.subTest(argv=argv):
                # F18 part 1 (contract 9) reads the progress issues for their overturns.
                self.assertIn(argv[:2], (["pr", "list"], ["pr", "view"], ["issue", "view"],
                                         ["run", "list"], ["issue", "list"]))
                if argv[:2] == ["pr", "list"]:
                    self.assertEqual(argv, MERGED_ARGS)
        after = (self.project.status_lines(), self.project.head(),
                 (self.project.git_dir() / "troy-mode/hooks.log").read_bytes())
        self.assertEqual(after, self.before)


class RetroRefusalTests(FlowCase):
    """No release commit: exit 1. A bad tag, gh failing, no repository: exit 2."""

    def test_refusals(self):
        """Each case's exit code."""
        project = Project(STEPS[:12])
        fakes = Fakes(merged=[merged_pr(11, "[docs] Release v0.1.0")], issue_views=ISSUES)
        cases = {
            "no release commit": (["--tag", "v0.2.0"], fakes, 1),
            "tag without the patch": (["--tag", "v0.1"], fakes, 2),
            "gh fails": (["--tag", "v0.1.0"], Fakes(fail=True), 2),
            "control": (["--tag", "v0.1.0"], fakes, 0),
        }
        names = list(cases)
        outs = parallel(lambda n: project.run("retro", *cases[n][0], fakes=cases[n][1]), names)
        for name, out in zip(names, outs):
            with self.subTest(case=name):
                if cases[name][2] == 0:
                    self.report_of(out, 0, "retro")
                elif cases[name][2] == 1:
                    self.assertNotEqual(self.report_of(out, 1, "retro")["problems"], [])
                else:
                    self.assert_exit(out, 2)
        plain = new_dir("plain")
        out = run_engine(["retro", "--tag", "v0.1.0", "--repo", plain, "--json"], SCRATCH,
                         Fakes(fail=True))
        self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
