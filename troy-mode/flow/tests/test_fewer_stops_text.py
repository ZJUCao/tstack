"""F18 part 1's instruction text (F18 design 4.1 to 4.3, 5, 6, 9, 10; part 1 contract 11).

The Product Manager's instructions hold the list of waits and PM7; the Architect's hold
AR8 and AR2's ``Risky:`` line; the entry skill names every wait, the ``Wait:`` line, the
rulings, the premise attempt, the re-run of CI, the overturn headings, and a reach that
goes on to Troy's device test. Two old texts are gone.

Planted bug of design 13.2 caught here:

- "the reach ended after one feature": ``SkillTextTests.test_how_far_reaches_the_device_test``
  and ``test_how_far_names_the_ways_to_stop_earlier``.
"""

import re
import unittest

from flow_helpers import PLUGIN_ROOT
from test_entry_skill import SKILL, routing_section, section, split_skill

PRODUCT_MANAGER = PLUGIN_ROOT / "troy-mode/roles/product-manager.md"
ARCHITECT = PLUGIN_ROOT / "agents/troy-architect.md"
WAIT_IDS = tuple(f"W{n}" for n in range(1, 12))
SKILL_WORDS = ("ruling, round 3", "AR8", "PM7", "ruled-revision", "--premise", "Premise:",
               "principle-attack-the-premise", "gh run rerun", "--failed", "Overturn:",
               "Overturn carried out:", "Wait: W")
VERDICTS = ("fix", "does not block", "fixed", "not fixed")
GONE = ("If round 3 still ends in `changes-requested`, escalate.",
        "ask Troy whether to close that PR too")


def read(path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def headings(text: str) -> list:
    """The ATX heading lines of a text outside fenced blocks, trimmed."""
    found, fenced = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"^#{1,6} ", line):
            found.append(line.strip())
    return found


def steps_of(text: str) -> list:
    """The numbered step lines (``1. ...``) of a text."""
    return [line for line in text.split("\n") if re.match(r"^\d+\. \S", line)]


class ProductManagerTextTests(unittest.TestCase):
    """``troy-mode/roles/product-manager.md`` (contract 11; design 4.1, 4.3, 5.1)."""

    @classmethod
    def setUpClass(cls):
        """Reads the file and cuts out its sections."""
        cls.text = read(PRODUCT_MANAGER)
        cls.heads = headings(cls.text)
        cls.waits = section(cls.text, "## Waits for Troy")
        cls.tasks = {key: section(cls.text, f"### {key}")
                     for key in ("PM3 Acceptance", "PM6 Ideas", "PM7 Ruling")}

    def test_waits_section_comes_before_the_tasks(self):
        """A ``## Waits for Troy`` section, before ``## Tasks``."""
        self.assertIn("## Waits for Troy", self.heads)
        self.assertIn("## Tasks", self.heads)
        self.assertLess(self.heads.index("## Waits for Troy"), self.heads.index("## Tasks"))

    def test_waits_table_lists_w1_to_w11_in_order(self):
        """The section's table has one row per ID, ``| W1 |`` to ``| W11 |``, in order."""
        rows = [m.group(1) for m in re.finditer(r"^\| (W\d+) \|", self.waits, re.M)]
        self.assertEqual(rows, list(WAIT_IDS))

    def test_pm7_follows_pm6_with_steps(self):
        """``### PM7 Ruling`` right after ``### PM6 Ideas``, with numbered steps."""
        tasks = [h for h in self.heads if re.match(r"^### PM\d+ ", h)]
        self.assertEqual(tasks[-2:], ["### PM6 Ideas", "### PM7 Ruling"])
        self.assertTrue(steps_of(self.tasks["PM7 Ruling"]), self.tasks["PM7 Ruling"])

    def test_pm7_rules_each_finding(self):
        """PM7 names both verdicts of a finding, the check's two results, and changes no file."""
        text = self.tasks["PM7 Ruling"]
        for word in VERDICTS:
            with self.subTest(word=word):
                self.assertRegex(text, rf"\b{word}\b")
        self.assertRegex(text, r"(?i)change no file|changes no file")

    def test_pm3_and_pm6_answer_from_the_documents(self):
        """PM3 and PM6 answer a question from the approved documents; only a question that
        needs a document changed waits for Troy, as W6."""
        for key in ("PM3 Acceptance", "PM6 Ideas"):
            with self.subTest(task=key):
                text = self.tasks[key]
                self.assertRegex(text, r"\bW6\b")
                self.assertRegex(text, r"(?i)\banswer")
                self.assertRegex(text, r"(?i)\bapproved\b")


class ArchitectTextTests(unittest.TestCase):
    """``agents/troy-architect.md`` (contract 11; design 5.2, 7.2)."""

    @classmethod
    def setUpClass(cls):
        """Reads the file and cuts out its sections."""
        cls.text = read(ARCHITECT)
        cls.heads = headings(cls.text)
        cls.ar2 = section(cls.text, "### AR2 Design review")
        cls.ar8 = section(cls.text, "### AR8 Ruling")
        cls.report = section(cls.text, "## Report")

    def test_ar8_follows_ar7_with_steps(self):
        """``### AR8 Ruling`` right after ``### AR7 Batch plan``, with numbered steps."""
        tasks = [h for h in self.heads if re.match(r"^### AR\d+ ", h)]
        self.assertEqual(tasks[-2:], ["### AR7 Batch plan", "### AR8 Ruling"])
        self.assertTrue(steps_of(self.ar8), self.ar8)

    def test_ar8_rules_checks_and_escalates(self):
        """Each open finding ``fix`` or ``does not block`` with a sentence of reason; the
        check after the revision ``fixed`` or ``not fixed``; a document change is
        ``escalate``; no file changes."""
        for word in (*VERDICTS, "escalate"):
            with self.subTest(word=word):
                self.assertRegex(self.ar8, rf"\b{word}\b")
        self.assertRegex(self.ar8, r"(?i)\bone sentence\b")
        self.assertRegex(self.ar8, r"(?i)change no file")

    def test_ar2_ends_summary_with_the_risky_line(self):
        """AR2 ends Summary with ``Risky: no`` or ``Risky: <reason>``, from the fixed list."""
        self.assertIn("Risky: no", self.ar2)
        self.assertRegex(self.ar2, r"Risky: <[^<>\n]+>")
        self.assertIn("Summary", self.ar2)
        for word in ("stored data format", "deleted or moved", "prototypes", "network",
                     "subprocess", "credentials"):
            with self.subTest(word=word):
                self.assertIn(word, self.ar2.lower())

    def test_findings_line_names_ar2_and_ar8(self):
        """The report's ``Findings:`` line names both tasks that give findings."""
        lines = [line for line in self.report.split("\n") if line.startswith("Findings:")]
        self.assertEqual(len(lines), 1, self.report)
        self.assertRegex(lines[0], r"\bAR2\b")
        self.assertRegex(lines[0], r"\bAR8\b")


class SkillTextTests(unittest.TestCase):
    """``skills/troy-mode/SKILL.md`` (contract 11; design 4.2, 4.3, 5, 6, 9 F07)."""

    @classmethod
    def setUpClass(cls):
        """Reads the skill's body and its How far bullet."""
        cls.body = split_skill(read(SKILL))[1]
        routing = routing_section(cls.body)
        cls.how_far = [line for line in routing.split("\n") if line.startswith("- **How far")]

    def bullet(self) -> str:
        """The one ``- **How far`` bullet of the Routing section."""
        self.assertEqual(len(self.how_far), 1, self.how_far)
        return self.how_far[0]

    def test_names_every_wait(self):
        """Each ID W1 to W11 appears as a word."""
        for wait in WAIT_IDS:
            with self.subTest(wait=wait):
                self.assertRegex(self.body, rf"\b{wait}\b")

    def test_names_the_wait_option_and_line(self):
        """``--wait`` as an option of its own, and the comment line ``Wait: W``."""
        self.assertRegex(self.body, r"--wait(?![\w-])")
        self.assertIn("Wait: W", self.body)

    def test_names_rulings_premise_rerun_and_overturns(self):
        """The ruling heading, AR8, PM7, ``ruled-revision``, ``--premise``, ``Premise:``, the
        premise card, ``gh run rerun`` with ``--failed``, and both overturn headings."""
        for word in SKILL_WORDS:
            with self.subTest(word=word):
                self.assertIn(word, self.body)

    def test_how_far_reaches_the_device_test(self):
        """Planted bug "the reach ended after one feature": a feature-loop request reaches the
        rest of the version, up to Troy's device test."""
        bullet = self.bullet()
        self.assertRegex(bullet, r"(?i)\bdevice test\b")
        self.assertRegex(bullet, r"(?i)\bversion\b")

    def test_how_far_names_the_ways_to_stop_earlier(self):
        """Planted bug "the reach ended after one feature": Troy stops earlier by naming it,
        such as "only F04" or "stop after"."""
        bullet = self.bullet()
        self.assertIn("only F04", bullet)
        self.assertIn("stop after", bullet)

    def test_old_texts_are_gone(self):
        """The escalation at round 3 and the question about a closed idea's PR are gone."""
        self.assertNotEqual(self.body, "")
        for text in GONE:
            with self.subTest(text=text):
                self.assertNotIn(text, self.body)


if __name__ == "__main__":
    unittest.main()
