"""Text tests of the agent file that F17 step 2 changes (F17 design 7.2 H1, 12.2; contract 1, 3).

Written from F17 design 1.1 and the step 2 contract before the change. H1 gives the
Architect's task AR2 a sentence of troy-mode's own: step 2 gains one paragraph, after the
seven checklist items and the paragraph about the summary in the brief's Input, and before
step 3. The paragraph is the contract's word for word, as a paragraph of its own, and it is
indented as the Input paragraph is, so that Markdown keeps it inside step 2's list item.

The agent file's Common rules stay an exact copy of ``troy-mode/roles/common.md``:
``test_roles.CommonRulesTests.test_each_agent_ends_with_an_exact_copy_of_common_md`` checks
that for every agent file, the Architect's among them, so it is not repeated here.

On step 1's code (``5b92ff4``) both tests fail: AR2's step 2 has no such paragraph.

Run from the repository root:
python -m unittest discover -s troy-mode/dev/tests -p test_f17_files.py -v
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ARCHITECT = REPO / "agents" / "troy-architect.md"
WHERE = "agents/troy-architect.md, AR2"
# H1's paragraph, from the step 2 contract (section 1).
H1 = ("A design that departs from the words of the architecture or of an ADR fails the item it "
      "breaks, also when you judge the departure right or read the ADR as covering it. Ask the "
      "design to name the rule, and to put the change to Troy as a point (requirements 5.7). "
      "Read each exception as written.")
# How step 2, its paragraph about the Input, and step 3 start, and the checklist's last item.
CHECKLIST_START = "2. Check the design against the seven checklist items:"
SEVENTH_ITEM = ("- The summary for Troy says what the design says, and lists every point Troy "
                "decides.")
INPUT_START = "The brief's Input holds the summary for the seventh item."
STEP_3_START = "3. Fill section 4 of the design and of its mirror:"
STEP = re.compile(r"^(\d+)\. ")


def read(path: Path) -> str:
    """A file's text with LF line endings, or "" when it is missing."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n") if path.is_file() else ""


def normalize(text: str) -> str:
    """Collapses each run of whitespace to one space and trims the ends."""
    return " ".join(text.split())


def task_lines(text: str, heading: str) -> list:
    """The lines under a ``### `` task heading, up to the next heading of level 1 to 3.

    Fenced code blocks are skipped when looking for the end.

    Args:
        text: The agent file.
        heading: The task heading's title, such as ``AR2 Design review``.

    Returns:
        The lines after the heading, or [] when there is no such heading.
    """
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == f"### {heading}"), None)
    if start is None:
        return []
    found, fence = [], False
    for line in lines[start + 1:]:
        if re.match(r"^ {0,3}(```|~~~)", line):
            fence = not fence
        if not fence and re.match(r"^#{1,3} ", line):
            break
        found.append(line)
    return found


def steps(lines: list) -> dict:
    """A task's numbered steps.

    Args:
        lines: The task's lines.

    Returns:
        Each step's number mapped to its lines, from the line that starts ``<n>. `` to the next
        such line or the end, trailing blank lines left out.
    """
    found, current = {}, None
    for line in lines:
        match = STEP.match(line)
        if match:
            current = found[int(match.group(1))] = []
        if current is not None:
            current.append(line)
    for body in found.values():
        while body and not body[-1].strip():
            body.pop()
    return found


def paragraphs(lines: list) -> list:
    """The blocks of lines that blank lines separate, each a list of lines, in order."""
    found, current = [], []
    for line in lines + [""]:
        if line.strip():
            current.append(line)
        elif current:
            found.append(current)
            current = []
    return found


def indent(line: str) -> str:
    """A line's leading whitespace."""
    return line[:len(line) - len(line.lstrip())]


class ArchitectReviewTests(unittest.TestCase):
    """H1's paragraph in the Architect's task AR2, step 2 (design 7.2 H1; contract 1)."""

    @classmethod
    def setUpClass(cls):
        """Reads the agent file and splits AR2 into its steps, and step 2 into paragraphs."""
        cls.text = read(ARCHITECT)
        cls.steps = steps(task_lines(cls.text, "AR2 Design review"))
        cls.blocks = paragraphs(cls.steps.get(2, []))

    def texts(self) -> list:
        """Step 2's paragraphs, each with its whitespace collapsed."""
        return [normalize("\n".join(block)) for block in self.blocks]

    def test_step_2_ends_with_h1s_paragraph(self):
        """Step 2 is the checklist, the paragraph about the summary in Input, and then H1's
        paragraph, word for word; step 3 follows it."""
        self.assertIn(2, self.steps, f"{WHERE}: no step 2")
        self.assertIn(3, self.steps, f"{WHERE}: no step 3")
        self.assertTrue(self.steps[3][0].startswith(STEP_3_START), self.steps[3][0])
        texts = self.texts()
        self.assertEqual(len(texts), 3, f"{WHERE}: step 2's paragraphs: {texts}")
        self.assertTrue(texts[0].startswith(CHECKLIST_START), texts[0])
        self.assertIn(SEVENTH_ITEM, [line.strip() for line in self.blocks[0]])
        self.assertTrue(texts[1].startswith(INPUT_START), texts[1])
        self.assertEqual(texts[2], H1, f"{WHERE}: step 2's last paragraph is not H1's")

    def test_h1s_paragraph_is_inside_step_2_once(self):
        """H1's paragraph is indented as the Input paragraph is, so it stays in step 2's list
        item, and the agent file holds it once."""
        found = [block for block, text in zip(self.blocks, self.texts()) if text == H1]
        self.assertEqual(len(found), 1, f"{WHERE}: step 2 holds H1's paragraph {len(found)} "
                                        f"times: {self.texts()}")
        inputs = [block for block, text in zip(self.blocks, self.texts())
                  if text.startswith(INPUT_START)]
        self.assertEqual(len(inputs), 1, self.texts())
        margin = indent(inputs[0][0])
        self.assertTrue(margin, f"{WHERE}: the Input paragraph is not indented")
        for line in found[0]:
            with self.subTest(line=line):
                self.assertEqual(indent(line), margin, line)
        self.assertEqual(normalize(self.text).count(H1), 1)


if __name__ == "__main__":
    unittest.main()
