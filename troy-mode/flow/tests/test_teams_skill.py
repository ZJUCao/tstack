"""AR7 and the entry skill with teams (F20 design 3.4, 3.6 to 3.8, 5, 6; contract P8, P9).

Written from F20 design version 1.3 and the part 2 contract before the code exists.

- P8: ``brief --task AR7 --item <version>`` gives the plan run's brief, and ``--task
  AR7 --item <F ID> [--title <PR title>]`` the check run's, at any stage; the role is
  the Architect and the agent ``tstack:troy-architect``. ``agents/troy-architect.md``
  has ``### AR7 Batch plan``, which describes both runs, the plan's fixed form (P1's
  feature and order lines, in one fenced block in Summary), and that AR7 changes no
  file; its Report section lists AR7 under ``done``.
- P9: ``skills/troy-mode/SKILL.md`` names ``team start``, ``team end``, ``plan``,
  ``merge-check``, AR7, ``--repo``, ``team-busy``, ``run_in_background``, and "approve
  all" (or "全部批准"), and keeps every heading it had at commit 10e788d.

Planted bugs caught here:

- AR7 missing from the agent file: ``AgentFileTests.test_ar7_heading_under_tasks`` and
  the other ``AgentFileTests``.
- AR7 refused by ``brief`` outside its stages: ``BriefTests.test_check_run_at_any_stage``.
- A heading of the skill dropped: ``SkillTests.test_keeps_every_heading``.
"""

import re
import unittest

from flow_helpers import (
    F01, F02, FIVE, PLUGIN_ROOT, FlowCase, Project, base_files, base_step, parallel, stages,
)

ARCHITECT = PLUGIN_ROOT / "agents/troy-architect.md"
SKILL = PLUGIN_ROOT / "skills/troy-mode/SKILL.md"
AGENT = "tstack:troy-architect"
FEATURE_FORM = re.compile(r"modules: [^;\n]+; interfaces: [^;\n]+; documents: \S")
ORDER_FORM = re.compile(r"\S+ after \S+ \S+/6")
NO_FILE = re.compile(r"\bno files?\b|changes nothing|Changed files: None", re.I)
# Every heading of skills/troy-mode/SKILL.md at commit 10e788d, in order.
SKILL_HEADINGS = (
    "# troy-mode", "## Start", "## The engine", "### Text for GitHub", "## Routing",
    "## Running a role", "### The report", "## The summary for Troy", "## Feature loop",
    "### One stage", "### PR 6: the real run", "### Local checks", "### Rounds and attempts",
    "### Comments", "### Merging", "## Side PRs", "### Disputed test", "### Coverage gap",
    "### New dependency (R16)", "## Bug fix", "## Requirement change", "## Version release",
    "### The version test plan (D70)", "### The release steps", "### Failures and bugs (D74)",
    "### Patch releases (D75)", "### Retrospective (D76)", "## Rule change",
    "### A project rule", "### Changing and retiring rules (D84)",
    "### A rule for every project (D83)", "## Issues for Troy", "### The sync (D141)",
    "### Progress issues (D142)", "### Troy's comments on issues (D145)", "### Ideas (D143)",
    "### Headings on issues (design 8.4)", "## Escalation", "## Project setup", "## Upgrade",
    "## Work outside the pipeline", "## Continue", "## Reports",
)
SKILL_NAMES = {
    "team start": r"\bteam start\b",
    "team end": r"\bteam end\b",
    "plan": r"troy_flow\.py plan(?![\w-])",
    "merge-check": r"troy_flow\.py merge-check(?![\w-])",
    "AR7": r"\bAR7\b",
    # The engine's --repo for a team; 10e788d's skill has only gh's "--repo <owner>/<name>".
    "--repo": r"--repo(?![\w-])(?! <owner>)",
    "team-busy": r"\bteam-busy\b",
    "run_in_background": r"\brun_in_background\b",
    "approve all": r"approve all|全部批准",
}


def read_text(path) -> str:
    """A file's text with LF line endings, or "" when it does not exist."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def headings(text: str) -> list:
    """The ATX heading lines of a Markdown text, outside fenced code blocks."""
    found, fence = [], None
    for line in text.split("\n"):
        stripped = line.strip()
        if fence is None and stripped[:3] in ("```", "~~~"):
            fence = stripped[:3]
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        if re.match(r"^#{1,6} \S", line):
            found.append(line.rstrip())
    return found


def section(text: str, heading: str) -> str:
    """The text under one heading line, up to the next heading of its level or higher."""
    lines = text.split("\n")
    if heading not in lines:
        return ""
    start = lines.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    body, fence = [], None
    for line in lines[start + 1:]:
        stripped = line.strip()
        if fence is None and stripped[:3] in ("```", "~~~"):
            fence = stripped[:3]
        elif fence is not None and stripped.startswith(fence):
            fence = None
        elif fence is None:
            match = re.match(r"^(#{1,6}) \S", line)
            if match and len(match.group(1)) <= level:
                break
        body.append(line)
    return "\n".join(body).strip()


# ------------------------------------------------------------------ briefs

_PROJECTS: dict = {}


def shared(stage: int) -> Project:
    """A clone with F01 accepted and F02 at the given stage, built on first use."""
    if stage not in _PROJECTS:
        _PROJECTS[stage] = Project([base_step(base_files(FIVE)), *stages(F01, 6),
                                    *stages(F02, stage - 1)])
    return _PROJECTS[stage]


class BriefTests(FlowCase):
    """``brief --task AR7`` for the plan run and the check run (contract P8)."""

    @classmethod
    def setUpClass(cls):
        """The plan run for v0.1, and the check run for F02 at stages 1, 3, 5, and 6."""
        cases = [("v0.1", 1, None), ("F02", 1, None), ("F02", 3, None), ("F02", 5, None),
                 ("F02", 6, None), ("F02", 1, F02.title(1))]
        for stage in sorted({c[1] for c in cases}):
            shared(stage)

        def run(case):
            """Runs one AR7 brief."""
            item, stage, title = case
            args = ["brief", "--task", "AR7", "--item", item]
            if title is not None:
                args += ["--title", title]
            return shared(stage).run(*args)
        cls.cases = cases
        cls.outs = dict(zip(cases, parallel(run, cases)))

    def brief_report(self, case) -> dict:
        """One case's brief report: exit 0, AR7, the Architect, and its agent."""
        report = self.report_of(self.outs[case], 0, "brief")
        self.assertEqual(("AR7", "architect"), (report.get("task"), report.get("role")))
        self.assertEqual(AGENT, (report.get("agent") or {}).get("subagent_type"))
        task_line = next((line for line in str(report.get("prompt", "")).split("\n")
                          if line.startswith("Task: ")), "")
        self.assertTrue(task_line.startswith("Task: AR7"), task_line)
        return report

    def test_plan_run_for_a_version(self):
        """``--item v0.1``: the plan run's brief, for the version."""
        self.assertEqual("v0.1", self.brief_report(("v0.1", 1, None)).get("item"))

    def test_check_run_at_any_stage(self):
        """``--item F02`` at stages 1, 3, 5, and 6: the check run's brief each time.

        Planted bug caught: AR7 refused by brief outside its stages.
        """
        for stage in (1, 3, 5, 6):
            with self.subTest(stage=stage):
                self.assertEqual("F02", self.brief_report(("F02", stage, None)).get("item"))

    def test_check_run_with_the_design_prs_title(self):
        """``--title`` names the PR whose design AR7 checks."""
        report = self.brief_report(("F02", 1, F02.title(1)))
        self.assertEqual(F02.title(1), report.get("title"))


# -------------------------------------------------------------- agent file

class AgentFileTests(unittest.TestCase):
    """``agents/troy-architect.md``'s AR7 (contract P8, design 3.4 and 6)."""

    @classmethod
    def setUpClass(cls):
        """Reads the agent file once."""
        cls.text = read_text(ARCHITECT)
        cls.ar7 = section(cls.text, "### AR7 Batch plan")

    def test_ar7_heading_under_tasks(self):
        """``### AR7 Batch plan`` once, inside ``## Tasks`` and after AR6.

        Planted bug caught: AR7 missing from the agent file.
        """
        found = headings(self.text)
        self.assertEqual(1, found.count("### AR7 Batch plan"), found)
        tasks, report = found.index("## Tasks"), found.index("## Report")
        at = found.index("### AR7 Batch plan")
        self.assertTrue(tasks < at < report, found)
        ar6 = next(i for i, h in enumerate(found) if h.startswith("### AR6 "))
        self.assertLess(ar6, at, found)

    def test_ar7_describes_both_runs(self):
        """The task has text, and names its plan run and its check run."""
        self.assertTrue(self.ar7, "AR7 has no text")
        self.assertRegex(self.ar7, re.compile(r"\bplan\b", re.I))
        self.assertRegex(self.ar7, re.compile(r"\bcheck\b", re.I))

    def test_ar7_gives_the_plans_fixed_form(self):
        """A feature line and an order line in P1's form, in a fenced block in Summary."""
        self.assertRegex(self.ar7, FEATURE_FORM)
        self.assertRegex(self.ar7, ORDER_FORM)
        self.assertIn("Summary", self.ar7)
        self.assertRegex(self.ar7, re.compile(r"fenced|```|~~~", re.I))

    def test_ar7_changes_no_file(self):
        """The task says that AR7 changes no file."""
        self.assertRegex(self.ar7, NO_FILE)

    def test_report_lists_ar7_under_done(self):
        """The Report section's ``done`` row names AR7."""
        report = section(self.text, "## Report")
        rows = [line for line in report.split("\n") if re.match(r"^\|\s*`?done`?\s*\|", line)]
        self.assertEqual(1, len(rows), report)
        self.assertRegex(rows[0], r"\bAR7\b")


# ------------------------------------------------------------------ skill

class SkillTests(unittest.TestCase):
    """``skills/troy-mode/SKILL.md`` with teams (contract P9)."""

    @classmethod
    def setUpClass(cls):
        """Reads the skill once."""
        cls.text = read_text(SKILL)

    def test_names_the_team_steps(self):
        """team start, team end, plan, merge-check, AR7, --repo, team-busy,
        run_in_background, and the one answer for every waiting PR."""
        for name, pattern in SKILL_NAMES.items():
            with self.subTest(name=name):
                self.assertRegex(self.text, pattern)

    def test_keeps_every_heading(self):
        """Every heading the skill had at commit 10e788d is still there, in the same order.

        Planted bug caught: a heading of the skill dropped.
        """
        found = headings(self.text)
        for heading in SKILL_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, found)
        kept = [h for h in found if h in SKILL_HEADINGS]
        self.assertEqual(list(SKILL_HEADINGS), kept)


if __name__ == "__main__":
    unittest.main()
