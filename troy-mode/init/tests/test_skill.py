"""Skill group (F06 design 2, 3.1, and 7): skills/troy-init/SKILL.md."""

import re
import unittest

from init_helpers import PLUGIN_ROOT

SKILL = PLUGIN_ROOT / "skills/troy-init/SKILL.md"
NAMED_TEXTS = (
    "${CLAUDE_PLUGIN_ROOT}/troy-mode/init/troy_init.py",
    "--dry-run --json",
    "git init -b main",
    "gh repo create",
    "--private",
    "git switch -c troy-mode/init origin/main",
    "--chmod=+x",
    "[rules] Set up troy-mode",
    "[rules] Upgrade troy-mode to <version>",
    "troy_check.py pr",
    "gh pr create --base main",
    "gh pr checks <number> --watch",
    "gh pr merge <number> --rebase --delete-branch --match-head-commit",
    "git pull --ff-only",
)


def split_skill(text: str) -> tuple:
    """Splits SKILL.md into its front matter fields and the text after it."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---":
        return {}, text
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip().strip("\"'")
    return fields, "\n".join(lines[end + 1:])


class SkillTest(unittest.TestCase):
    """The skill Troy types to run troy-init."""

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once."""
        cls.text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.fields, cls.body = split_skill(cls.text)

    def test_skill_front_matter_names_troy_init(self):
        """The front matter's name is troy-init."""
        self.assertEqual(self.fields.get("name"), "troy-init")

    def test_skill_runs_only_when_troy_types_it(self):
        """The front matter sets disable-model-invocation to true."""
        self.assertEqual(self.fields.get("disable-model-invocation"), "true")

    def test_skill_has_a_description(self):
        """The front matter has a description that is not empty."""
        self.assertNotEqual(self.fields.get("description", ""), "")

    def test_skill_names_the_three_steps(self):
        """The text names setup, lang, and upgrade."""
        for step in ("setup", "lang", "upgrade"):
            with self.subTest(step=step):
                self.assertRegex(self.body, rf"\b{step}\b")

    def test_skill_names_the_engine_and_the_pr_flow_commands(self):
        """The text names the engine and every command of the PR flow (design 7)."""
        for text in NAMED_TEXTS:
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_skill_forbids_git_add_all(self):
        """Every sentence that mentions git add -A says not to use it."""
        sentences = [s for s in re.split(r"(?<=[.!?:])\s+", self.body) if "git add -A" in s]
        self.assertNotEqual(sentences, [])
        for sentence in sentences:
            with self.subTest(sentence=sentence):
                self.assertRegex(sentence, re.compile(r"\b(never|not|no)\b", re.I))


if __name__ == "__main__":
    unittest.main()
