"""F18 part 2's instruction text and its limits (F18 design 7, 9, 10; part 2 contract 0 and 8).

The entry skill names the spot check comment, TM8's real-run ruling, ``spot-off``,
``spot_evidence``, the report's line for spot checks, and the two config keys; its section
"Comments" names AR2's ``Risky:`` line and "Continue" names ``spot-off``. The Product
Manager's W3 row names risky PRs.

That part 2 changes none of the role exam's instruction set is a property of its build,
not of the code after it: ``troy_exam.py affected`` checks it for the PR (F16 design 9.2),
so no test pins today's instruction hash, which every later change of the set would fail.
"""

import unittest

from flow_helpers import PLUGIN_ROOT
from spot_helpers import lf_text
from test_entry_skill import SKILL, section, split_skill

PRODUCT_MANAGER = PLUGIN_ROOT / "troy-mode/roles/product-manager.md"
SKILL_WORDS = ("Spot check for Troy: review after the merge", "Test Manager ruling, real run",
               "spot-off", "spot_evidence", "Spot checks, after the merge", "[flow] spot_checks",
               "spot_check_every")


class SkillTextTests(unittest.TestCase):
    """``skills/troy-mode/SKILL.md`` (contract 8)."""

    @classmethod
    def setUpClass(cls):
        """Reads the skill's body."""
        cls.body = split_skill(lf_text(SKILL))[1]

    def test_names_spot_checks(self):
        """Each phrase of contract 8 appears."""
        for word in SKILL_WORDS:
            with self.subTest(word=word):
                self.assertIn(word, self.body)

    def test_comments_section_names_the_risky_line(self):
        """``Risky:`` in the section "Comments", where AR2's line is posted."""
        self.assertIn("Risky:", section(self.body, "### Comments"))

    def test_continue_section_names_spot_off(self):
        """``spot-off`` in the section "Continue"."""
        self.assertIn("spot-off", section(self.body, "## Continue"))


class ProductManagerTextTests(unittest.TestCase):
    """``troy-mode/roles/product-manager.md`` (contract 8)."""

    def test_w3_row_names_risky_prs(self):
        """The W3 row of "Waits for Troy" names risky PRs."""
        rows = [line for line in lf_text(PRODUCT_MANAGER).split("\n") if line.startswith("| W3 |")]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("risky", rows[0])


if __name__ == "__main__":
    unittest.main()
