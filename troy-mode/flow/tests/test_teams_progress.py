"""Progress with teams (F20 design 3.12, 8.1; part 2 contract P3 and P5).

Written from F20 design version 1.3 and the part 2 contract before the code exists.

- P3, the progress file: ``status --write-progress`` in teams mode writes ``- Teams:
  <n>`` right after the ``Current version`` line, one line per team, and the ``May
  start`` and ``Needs a plan`` lines when their lists are not empty. Outside teams
  mode the file keeps today's shape exactly.
- P5, progress issues (F15 design 4.1): a feature in ``may_start``, or with a team
  worktree, has an open progress issue, as the next feature has today. ``issues``
  lists the ``create`` actions.

The features and fixtures are those of test_teams_status.py: F01 to F06, with F02
hard on F01, F03 soft on F01, and F04 hard on F02. The issue cases use F01 to F05,
which have Chinese names in issues_helpers.

Planted bugs caught here:

- The progress file changed outside teams mode:
  ``ProgressFileTests.test_outside_teams_mode_the_file_is_as_today``.
- A team left out of the progress file, or its stage wrong:
  ``ProgressFileTests.test_teams_follow_the_current_version_line``.
- Only the next feature given a progress issue in teams mode:
  ``ProgressIssueTests.test_every_feature_that_may_start_gets_one`` and
  ``test_team_feature_gets_one_and_a_held_feature_none``.
"""

import unittest

from flow_helpers import (
    F01, F02, F05, FIVE, PROGRESS, PROGRESS_FIELDS, TWO, Fakes, Project, base_files, base_step,
    parallel, stage_pr, stages,
)
from issues_helpers import ALL_LABELS, IssuesCase, progress_title, project_files, stage_prs
from teams2_helpers import SIX, TeamFakes, TeamsCase, add_team, write_plan

BASE = base_step(base_files(SIX))
A = (BASE, *stages(F01, 6))
B = (*A, *stages(F02, 2), *stages(F05, 1))
C6 = (*A, *stages(F02, 6))
OUT = (base_step(base_files(TWO)), *stages(F01, 2))
ALL_READY = ["F02", "F03", "F05", "F06"]
FEATURES = {f.id: f for f in FIVE}
ISSUES_A = (base_step(project_files(FIVE)), *stages(F01, 6))


def progress_case(spec: dict) -> tuple:
    """Builds a clone with its teams and plan, and runs ``status --write-progress --json``.

    Args:
        spec: ``steps``, ``teams`` (made in order), ``plan`` (IDs or None), and ``prs``.

    Returns:
        ``(project, outcome)``.
    """
    project = Project(spec["steps"])
    for item in spec.get("teams", ()):
        add_team(project, item)
    if spec.get("plan") is not None:
        write_plan(project, spec["plan"])
    fakes = TeamFakes(spec.get("prs", ()))
    return project, project.run("status", "--write-progress", fakes=fakes)


PROGRESS_CASES = {
    "two teams": {"steps": B, "teams": ["F05", "F02"], "plan": ["F03", "F06"],
                  "prs": [stage_pr(52, F02, 3)]},
    "needs a plan": {"steps": B, "teams": ["F02", "F05"], "plan": ["F03"]},
    "accepted team": {"steps": C6, "teams": ["F02"], "plan": ["F03", "F05", "F06"]},
    "all teams": {"steps": A, "teams": ["F06", "F02", "F05", "F03"], "plan": ALL_READY},
    "outside": {"steps": OUT},
}
_RESULTS: dict = {}


def results() -> dict:
    """Runs every progress case once, side by side, on first use."""
    if not _RESULTS:
        names = list(PROGRESS_CASES)
        _RESULTS.update(zip(names, parallel(progress_case, [PROGRESS_CASES[n] for n in names],
                                            workers=5)))
    return _RESULTS


class ProgressFileTests(TeamsCase):
    """The progress file in teams mode and outside it (contract P3)."""

    def lines(self, name: str) -> list:
        """The case's progress file lines; the run must exit 0 and write the file."""
        project, out = results()[name]
        report = self.report_of(out, 0, "status")
        self.assertIs(report["progress"]["written"], True, out.describe())
        return project.read(PROGRESS).split("\n")

    def team_lines(self, name: str, count: int) -> list:
        """The ``Teams`` line's value and the team lines after it, which must follow
        ``Current version`` directly."""
        lines = self.lines(name)
        start = next((i for i, line in enumerate(lines) if line.startswith("- Current version:")),
                     None)
        self.assertIsNotNone(start, lines)
        self.assertEqual(f"- Teams: {count}", lines[start + 1], "\n".join(lines))
        return lines[start + 2:start + 2 + count]

    def test_teams_follow_the_current_version_line(self):
        """Two teams by ID: F02 at stage 3 with its open PR, F05 at stage 2 with TM1 next."""
        found = self.team_lines("two teams", 2)
        prefixes = ("  - F02 Count lines: stage 3 of 6. ", "  - F05 Watch folders: stage 2 of 6. ")
        for line, prefix in zip(found, prefixes):
            with self.subTest(line=line):
                self.assertTrue(line.startswith(prefix), found)
                self.assertTrue(line[len(prefix):].strip(), "no next action on the team line")
        self.assertIn("#52", found[0])
        self.assertTrue("TM1" in found[1] or F05.title(2) in found[1], found[1])

    def test_may_start_line_without_a_needs_line(self):
        """F03 and F06 may start and nothing needs a plan: only the May start line."""
        lines = self.lines("two teams")
        self.assertIn("- May start: F03, F06", lines)
        self.assertFalse([line for line in lines if line.startswith("- Needs a plan")], lines)

    def test_needs_a_plan_line(self):
        """F06 has no feature line: ``- Needs a plan: F06`` and ``- May start: F03``."""
        lines = self.lines("needs a plan")
        self.team_lines("needs a plan", 2)
        self.assertIn("- May start: F03", lines)
        self.assertIn("- Needs a plan: F06", lines)

    def test_accepted_team_says_accepted(self):
        """F02 accepted with its worktree: ``accepted`` in place of the stage."""
        found = self.team_lines("accepted team", 1)
        self.assertTrue(found[0].startswith("  - F02 Count lines: accepted"), found)
        lines = self.lines("accepted team")
        self.assertIn("- May start: F03, F05, F06", lines)
        self.assertIn("- Needs a plan: F04", lines)

    def test_no_list_lines_when_both_are_empty(self):
        """Every ready feature has a team: four team lines and neither list line."""
        found = self.team_lines("all teams", 4)
        self.assertEqual(["F02", "F03", "F05", "F06"], [line[4:7] for line in found])
        lines = self.lines("all teams")
        self.assertFalse([line for line in lines
                          if line.startswith(("- May start", "- Needs a plan"))], lines)

    def test_outside_teams_mode_the_file_is_as_today(self):
        """One ready feature, no team: the heading and the eight fields in order, nothing else.

        Planted bug caught: the progress file changed outside teams mode.
        """
        lines = self.lines("outside")
        self.assertEqual(["# Progress", ""], lines[:2])
        body = [line for line in lines[2:] if line]
        self.assertEqual(list(PROGRESS_FIELDS), [line[2:].split(":")[0] for line in body], body)
        self.assertFalse([line for line in lines if line.startswith(("  - ", "- Teams"))], lines)


class ProgressIssueTests(IssuesCase):
    """Progress issues for the features that may start or have a team (contract P5)."""

    @classmethod
    def setUpClass(cls):
        """Two clones, F01 accepted: every ready feature planned; and F05's team with
        ``F03 after F02 1/6``."""
        def run(teams_and_orders):
            """Builds one clone and runs ``issues --json`` in it."""
            teams, orders = teams_and_orders
            project = Project(ISSUES_A)
            for item in teams:
                add_team(project, item)
            write_plan(project, ["F02", "F03", "F05"], orders)
            fakes = Fakes(labels=list(ALL_LABELS), all_prs=stage_prs(F01, 6))
            return project, project.run("issues", fakes=fakes), fakes
        cls.free, cls.teams = parallel(run, [((), ()), (("F05",), (("F03", "F02", 1),))])

    def creates(self, result) -> dict:
        """The run's create actions by item, every one checked; only read calls made."""
        project, out, fakes = result
        report = self.issues_report(out)
        self.assert_read_only(fakes)
        found = {}
        for action in report["actions"]:
            if action["action"] == "create" and action["kind"] == "progress":
                self.assert_create(action, project, "progress", action["item"],
                                   progress_title(FEATURES[action["item"]]))
                found[action["item"]] = action
        return found

    def test_every_feature_that_may_start_gets_one(self):
        """F02, F03, and F05 may start: each gets a progress issue, not only the next one."""
        self.assertEqual(["F02", "F03", "F05"], sorted(self.creates(self.free)))

    def test_team_feature_gets_one_and_a_held_feature_none(self):
        """F05 has a team, F02 may start, F03 waits for F02's design: F02 and F05 only."""
        self.assertEqual(["F02", "F05"], sorted(self.creates(self.teams)))


if __name__ == "__main__":
    unittest.main()
