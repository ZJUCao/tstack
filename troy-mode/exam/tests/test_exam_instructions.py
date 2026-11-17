"""The instruction set group (F16 design 9.1, 9.2, 14.1): its files and its hash.

The hash changes with each listed file and with each of the two SKILL.md
sections, and not with other SKILL.md sections or other files; CRLF does
not change it; a folder and its git commit hash the same. ``affected``
finding no case for a refactor that renders the same briefs runs end to end
in test_exam_cli.AffectedTests.

Planted bug of design 14.2 caught here:

- "the hash leaving out the templates": ListTests.test_instruction_files and
  HashTests.test_each_listed_file_changes_the_hash (the troy-mode/templates/ subtests)
  and test_a_new_template_changes_the_hash.
"""

import ast
import re
import unittest

from exam_helpers import REPO, git, make_repo, new_dir, write_file
from troyexam.instructions import (BRIEF, FIXED, SKILL, SKILL_SECTIONS, FolderTree, GitTree,
                                   brief_modules, instruction_files, instruction_hash,
                                   named_skills, short_hash, skill_sections)

FLOW = "troy-mode/flow/troyflow"
SKILL_TEXT = ("---\nname: troy-mode\n---\n\n# troy-mode\n\n## Start\n\nStart text.\n\n"
              "## Running a role\n\nRole text.\n\n### The report\n\nReport text.\n\n"
              "## The summary for Troy\n\nSummary text.\n\n## Feature loop\n\nLoop text.\n\n"
              "### One stage\n\nStage text.\n")
FILES = {
    "README.md": "# tstack\n",
    "agents/troy-developer.md": "# Developer\n\nWrite prose by "
                                "${CLAUDE_PLUGIN_ROOT}/skills/technical-writing/SKILL.md.\n",
    "agents/troy-test-manager.md": "# Test Manager\n\nRead skills/benchmark-checklist/ and "
                                   "skills/troy-mode/SKILL.md.\n",
    "agents/helper.md": "# Helper\n\nUse skills/other/SKILL.md.\n",
    "troy-mode/roles/common.md": "# Common\n\nWrite by skills/technical-writing/SKILL.md.\n",
    "troy-mode/roles/product-manager.md": "# Product Manager\n",
    "troy-mode/templates/feature-design.md": "# Design\n",
    "troy-mode/templates/sub/table.md": "| a |\n",
    "troy-mode/flow/troy_flow.py": "print(1)\n",
    f"{FLOW}/__init__.py": 'PLUGIN_PREFIX = "tstack:"\n',
    f"{FLOW}/brief.py": ("import re\n\nfrom . import PLUGIN_PREFIX, checksteps, summary\n"
                         "from .errors import FlowError\nfrom .rulebrief import make\n"
                         "from .stages import first, \\\n    second\n"),
    f"{FLOW}/checksteps.py": "import os\n",
    f"{FLOW}/summary.py": "from .sections import cut\n",
    f"{FLOW}/sections.py": "X = 1\n",
    f"{FLOW}/errors.py": "class FlowError(Exception):\n    pass\n",
    f"{FLOW}/rulebrief.py": "from . import summary\n",
    f"{FLOW}/stages.py": "Y = 2\n",
    f"{FLOW}/unrelated.py": "from .sections import cut\n",
    f"{FLOW}/status.py": "from . import brief\n",
    "skills/technical-writing/SKILL.md": "# Writing\n",
    "skills/technical-writing/reference/style.md": "# Style\n",
    "skills/benchmark-checklist/SKILL.md": "# Checklist\n",
    "skills/other/SKILL.md": "# Other\n",
    "skills/troy-mode/SKILL.md": SKILL_TEXT,
    "troy-mode/exam/troy_exam.py": "print(1)\n",
    "troy-mode/exam/troyexam/core.py": "Z = 3\n",
    "troy-mode/exam/cases/dv-x/case.toml": 'id = "dv-x"\n',
    "troy-mode/exam/tests/test_x.py": "T = 1\n",
    "docs/design.md": "# D\n",
}
EXPECTED = sorted([
    "agents/troy-developer.md", "agents/troy-test-manager.md",
    "skills/benchmark-checklist/SKILL.md", "skills/technical-writing/SKILL.md",
    "skills/technical-writing/reference/style.md",
    "troy-mode/exam/cases/dv-x/case.toml", "troy-mode/exam/troyexam/core.py",
    f"{FLOW}/__init__.py", f"{FLOW}/brief.py", f"{FLOW}/checksteps.py", f"{FLOW}/errors.py",
    f"{FLOW}/rulebrief.py", f"{FLOW}/sections.py", f"{FLOW}/stages.py", f"{FLOW}/summary.py",
    "troy-mode/roles/common.md", "troy-mode/templates/feature-design.md",
    "troy-mode/templates/sub/table.md"])
UNLISTED = ("README.md", "agents/helper.md", "skills/other/SKILL.md", f"{FLOW}/unrelated.py",
            f"{FLOW}/status.py", "troy-mode/flow/troy_flow.py", "troy-mode/exam/troy_exam.py",
            "troy-mode/exam/tests/test_x.py", "troy-mode/roles/product-manager.md",
            "docs/design.md")


def tree(changes: dict = None, crlf: bool = False) -> FolderTree:
    """A folder of FILES with changes (None deletes), as a FolderTree."""
    files = dict(FILES)
    for rel, content in (changes or {}).items():
        if content is None:
            files.pop(rel, None)
        else:
            files[rel] = content
    folder = new_dir("itree")
    for rel, content in files.items():
        write_file(folder, rel, content.replace("\n", "\r\n") if crlf else content)
    return FolderTree(folder)


def ast_closure(read) -> set:
    """brief.py's troyflow imports, followed through troyflow, by this file's own reading."""
    def deps(name: str) -> set:
        """The troyflow modules one module imports."""
        source = read(f"{FLOW}/{name}.py")
        found = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                if node.module:
                    found.add(node.module.split(".")[0])
                else:
                    found |= {a.name for a in node.names if read(f"{FLOW}/{a.name}.py")}
        return found
    seen, todo = {"brief", "__init__"}, ["brief", "__init__"]
    while todo:
        for dep in deps(todo.pop()):
            if dep not in seen:
                seen.add(dep)
                todo.append(dep)
    return {f"{FLOW}/{name}.py" for name in seen}


class ConstantTests(unittest.TestCase):
    """The list of design 9.1, held in one place (contract)."""

    def test_constants(self):
        """The fixed patterns, brief.py, SKILL.md, and its two sections."""
        self.assertEqual(tuple(FIXED), ("agents/troy-*.md", "troy-mode/roles/common.md",
                                        "troy-mode/templates/**", "troy-mode/exam/cases/**",
                                        "troy-mode/exam/troyexam/**"))
        self.assertEqual(BRIEF, "troy-mode/flow/troyflow/brief.py")
        self.assertEqual(SKILL, "skills/troy-mode/SKILL.md")
        self.assertEqual(tuple(SKILL_SECTIONS), ("Running a role", "The summary for Troy"))


class TreeTests(unittest.TestCase):
    """FolderTree and GitTree read the same files."""

    @classmethod
    def setUpClass(cls):
        """One folder and a repository with two commits of it."""
        cls.folder = tree()
        cls.repo = new_dir("igit") / "tstack"
        cls.first = make_repo(cls.repo, FILES)
        write_file(cls.repo, "troy-mode/templates/feature-design.md", "# Design, second\n")
        git(cls.repo, "add", "-A")
        git(cls.repo, "commit", "-q", "-m", "Second")
        cls.second = git(cls.repo, "rev-parse", "HEAD").strip()

    def test_files_and_read(self):
        """Every file, POSIX paths; bytes; None for a missing file."""
        self.assertEqual(sorted(self.folder.files()), sorted(FILES))
        self.assertEqual(self.folder.read("README.md"), b"# tstack\n")
        self.assertIsNone(self.folder.read("no/such/file.md"))

    def test_a_commit_reads_like_its_folder(self):
        """The first commit's files and hash equal the folder's."""
        commit = GitTree(self.repo, self.first)
        self.assertEqual(sorted(commit.files()), sorted(FILES))
        self.assertEqual(commit.read("README.md"), b"# tstack\n")
        self.assertIsNone(commit.read("no/such/file.md"))
        self.assertEqual(instruction_hash(commit), instruction_hash(self.folder))

    def test_each_commit_has_its_own_content(self):
        """The second commit's template, and its own hash."""
        second = GitTree(self.repo, self.second)
        self.assertEqual(second.read("troy-mode/templates/feature-design.md"),
                         b"# Design, second\n")
        self.assertNotEqual(instruction_hash(second), instruction_hash(GitTree(self.repo,
                                                                               self.first)))
        self.assertEqual(instruction_hash(GitTree(self.repo, "HEAD")), instruction_hash(second))


class ListTests(unittest.TestCase):
    """brief_modules, named_skills, and instruction_files (design 9.1)."""

    def test_brief_modules(self):
        """brief.py, __init__.py, and what brief.py imports, directly or through summary.py."""
        self.assertEqual(set(brief_modules(tree())), {
            f"{FLOW}/brief.py", f"{FLOW}/__init__.py", f"{FLOW}/checksteps.py",
            f"{FLOW}/summary.py", f"{FLOW}/sections.py", f"{FLOW}/errors.py",
            f"{FLOW}/rulebrief.py", f"{FLOW}/stages.py"})

    def test_named_skills(self):
        """The skills an agent file troy-*.md or common.md names, other than troy-mode."""
        self.assertEqual(set(named_skills(tree())), {"skills/technical-writing/",
                                                     "skills/benchmark-checklist/"})

    def test_instruction_files(self):
        """Sorted: the fixed patterns, the brief's modules, the named skills; not SKILL.md."""
        self.assertEqual(instruction_files(tree()), EXPECTED)

    def test_a_skill_newly_named_joins_the_list(self):
        """An agent file that names skills/other/ brings its files in."""
        found = instruction_files(tree({"agents/troy-developer.md":
                                        FILES["agents/troy-developer.md"]
                                        + "Also skills/other/SKILL.md.\n"}))
        self.assertIn("skills/other/SKILL.md", found)

    def test_a_module_newly_imported_joins_the_list(self):
        """brief.py importing unrelated.py brings it in."""
        found = instruction_files(tree({f"{FLOW}/brief.py": FILES[f"{FLOW}/brief.py"]
                                        + "from .unrelated import cut\n"}))
        self.assertIn(f"{FLOW}/unrelated.py", found)

    def test_this_repository(self):
        """tstack's own set: the parts design 9.1 names, and none it does not."""
        head = GitTree(REPO, "HEAD")
        found = set(instruction_files(head))
        files = set(head.files())
        agents = {f for f in files if re.fullmatch(r"agents/troy-[^/]+\.md", f)}
        templates = {f for f in files if f.startswith("troy-mode/templates/")}
        self.assertEqual(len(agents), 6)
        self.assertLessEqual(agents | templates | {"troy-mode/roles/common.md"}, found)
        self.assertEqual(set(brief_modules(head)),
                         ast_closure(lambda p: (head.read(p) or b"").decode("utf-8")))
        self.assertLessEqual({f"{FLOW}/brief.py", f"{FLOW}/summary.py", f"{FLOW}/checksteps.py",
                              f"{FLOW}/rulebrief.py"}, found)
        texts = "".join((head.read(f) or b"").decode("utf-8")
                        for f in sorted(agents) + ["troy-mode/roles/common.md"])
        named = {f"skills/{n}/" for n in re.findall(r"skills/([A-Za-z0-9_-]+)/", texts)
                 if n != "troy-mode"}
        self.assertEqual(set(named_skills(head)), named)
        self.assertLessEqual({"skills/technical-writing/", "skills/benchmark-checklist/"}, named)
        self.assertIn("skills/technical-writing/SKILL.md", found)
        for path in ("skills/troy-mode/SKILL.md", "agents/poteto-agent.md",
                     "troy-mode/roles/product-manager.md", f"{FLOW}/cli.py", f"{FLOW}/status.py",
                     "README.md"):
            with self.subTest(path=path):
                self.assertNotIn(path, found)


class SectionTests(unittest.TestCase):
    """skill_sections: the two role sections of the entry skill (design 9.1)."""

    def test_the_two_sections_with_their_subsections(self):
        """Running a role holds The report; neither holds the next section."""
        found = skill_sections(SKILL_TEXT)
        self.assertEqual(set(found), {"Running a role", "The summary for Troy"})
        self.assertIn("Role text.", found["Running a role"])
        self.assertIn("Report text.", found["Running a role"])
        self.assertNotIn("Summary text.", found["Running a role"])
        self.assertIn("Summary text.", found["The summary for Troy"])
        for name in found:
            for other in ("Start text.", "Loop text.", "Stage text."):
                self.assertNotIn(other, found[name])

    def test_a_missing_section_is_empty(self):
        """No such heading: an empty text."""
        self.assertEqual(skill_sections("# x\n\n## Start\n\nA.\n"),
                         {"Running a role": "", "The summary for Troy": ""})


class HashTests(unittest.TestCase):
    """instruction_hash (design 9.1, 9.3)."""

    @classmethod
    def setUpClass(cls):
        """The hash of the unchanged fixture."""
        cls.base = instruction_hash(tree())

    def test_shape_and_stability(self):
        """64 lower-case hex digits, the same for two copies; short_hash is its first 12."""
        self.assertRegex(self.base, r"^[0-9a-f]{64}$")
        self.assertEqual(instruction_hash(tree()), self.base)
        self.assertEqual(short_hash(self.base), self.base[:12])
        self.assertEqual(short_hash("3f9c2a1b7e04" + "0" * 52), "3f9c2a1b7e04")

    def test_each_listed_file_changes_the_hash(self):
        """One more line in any instruction file gives another hash."""
        for rel in EXPECTED:
            with self.subTest(file=rel):
                self.assertNotEqual(instruction_hash(tree({rel: FILES[rel] + "# more\n"})),
                                    self.base)

    def test_other_files_do_not_change_the_hash(self):
        """README, other agents and skills, unimported modules, the CLI, tests, the PM's file."""
        for rel in UNLISTED:
            with self.subTest(file=rel):
                self.assertEqual(instruction_hash(tree({rel: FILES[rel] + "# more\n"})),
                                 self.base)

    def test_the_two_skill_sections_change_the_hash(self):
        """Running a role, its subsection The report, and The summary for Troy."""
        for old in ("Role text.", "Report text.", "Summary text."):
            with self.subTest(text=old):
                changed = SKILL_TEXT.replace(old, old + " More.")
                self.assertNotEqual(instruction_hash(tree({SKILL: changed})), self.base)

    def test_other_skill_sections_do_not(self):
        """Start, Feature loop, and its subsections, and the front matter."""
        for old in ("Start text.", "Loop text.", "Stage text.", "name: troy-mode"):
            with self.subTest(text=old):
                changed = SKILL_TEXT.replace(old, old + " More.")
                self.assertEqual(instruction_hash(tree({SKILL: changed})), self.base)

    def test_a_new_template_changes_the_hash(self):
        """The list itself is hashed: an empty new template counts."""
        self.assertNotEqual(instruction_hash(tree({"troy-mode/templates/new.md": ""})), self.base)
        self.assertNotEqual(instruction_hash(tree({"skills/technical-writing/more.md": "x\n"})),
                            self.base)

    def test_a_rename_changes_the_hash(self):
        """The same content under another path."""
        table = FILES["troy-mode/templates/sub/table.md"]
        moved = tree({"troy-mode/templates/sub/table.md": None,
                      "troy-mode/templates/sub/table2.md": table})
        self.assertNotEqual(instruction_hash(moved), self.base)

    def test_a_module_that_joins_the_closure_is_hashed(self):
        """Once brief.py imports unrelated.py, a change to it changes the hash."""
        brief = FILES[f"{FLOW}/brief.py"] + "from .unrelated import cut\n"
        joined = instruction_hash(tree({f"{FLOW}/brief.py": brief}))
        unrelated = "from .sections import cut\nZ = 9\n"
        again = instruction_hash(tree({f"{FLOW}/brief.py": brief,
                                       f"{FLOW}/unrelated.py": unrelated}))
        self.assertNotEqual(joined, again)

    def test_crlf_does_not_change_the_hash(self):
        """A CRLF checkout hashes like its LF commit."""
        self.assertEqual(instruction_hash(tree(crlf=True)), self.base)


if __name__ == "__main__":
    unittest.main()
