"""Structure tests for troy-mode's role definitions (F04 design section 10.1).

F04's role files are prompts, not code, so these tests check their structure
against the F04 design (version 1.0) and the requirements. They cover the
seven groups of design section 10.1: Files, Frontmatter, Body, Must not,
Write scope, Common rules, and Product Manager. The expected names, models,
tools, task IDs, results, and write scopes sit in one block near the top of
this file, copied from design sections 3, 5.2, and 6. Each role's Must not
line is read from the roles table in requirements section 4 at test time.

The files tested:

- agents/troy-architect.md, troy-interface-designer.md, troy-test-manager.md,
  troy-developer.md, troy-test-engineer.md, and troy-code-reviewer.md.
- troy-mode/roles/common.md and troy-mode/roles/product-manager.md.

Format conventions. Design section 7 gives the agent file format. Where it
leaves a detail open, the tests require the following.

1. Encoding. Every role file is UTF-8 without a byte order mark, has LF line
   endings, and is not empty.
2. Files. agents/ holds exactly six troy-* entries, the six files above.
   troy-mode/roles/ holds exactly common.md and product-manager.md, so no
   mirror or other file sits beside them (D35).
3. Frontmatter. An agent file's first line is `---`, and the frontmatter ends
   at the next line that is `---`. Every line between is `key: value`, with a
   plain one-line value: no quotes, comments, or blank lines. The keys are
   name, description, tools, and model, each once. name is the file name
   without `.md`. model is as in design section 3. tools is a comma-separated
   list, for example `Read, Grep, Glob`, equal to design section 3 in the
   same order. description names the role as in design section 3 (for
   example "Developer") and holds the words "started only by the troy-mode
   entry skill", in any case.
4. Headings. Only ATX headings count: one to six `#` signs, a space, and a
   title. Lines inside fenced code blocks (``` or ~~~) are not headings.
5. Body. After the frontmatter, the level-1 and level-2 headings are exactly,
   in order: `# <Role name>` with the name as in design section 3, then
   `## Who you are`, `## Must not`, `## Write scope`, `## Tasks`, `## Report`,
   and `## Common rules`. Each of the six sections has text.
6. Tasks. A task ID is two capital letters and a number, for example DV1.
   Every level-3 heading under `## Tasks` is a task heading
   `### <ID> <title>`, and the headings equal the Task column of design
   section 6 exactly and in order, for example `### DV1 Mock`. Each task has
   text under its heading. No other heading in the file starts with a task
   ID. Task IDs may appear in prose anywhere.
7. Report. The `## Report` section holds exactly one fenced code block, in
   the shape of design section 5.2. Every non-blank line in it is
   `<Field>: <value>`, and the fields are Role, Task, Result, Changed files,
   Checks, Summary, Findings, and Question, in that order. The Result value
   lists the results the role sends, separated by ` | `, in the order of
   section 5.2. RESULTS below says which results each role sends.
8. Must not. The role's Must not cell in the requirements section 4 table
   appears in the role's `## Must not` section, after runs of whitespace are
   collapsed to one space in both. The match is case-sensitive.
9. Write scope. Every non-blank line of `## Write scope` is a Markdown bullet
   (`- `). A bullet names one thing, with its first backticked token: a path
   pattern, for example `` - `docs/adr/**` ``, or a path class, written as
   `` - The `source` path class ``. A path class token is one of F02's five
   classes (config, dependencies, tests, docs, source), and its line holds
   the words "path class". Text after the token is a qualifier. A role whose
   scope is empty has exactly one line, `- None`. The patterns and classes
   equal design section 3, with no repeats. For D37, the Architect's
   `docs/features/*/design*.md` bullet says "section 4" and not
   "except section 4", and the Interface Designer's says "except section 4".
10. Common rules. common.md is not empty, has no level-1 or level-2
    headings, and numbers its rules 1 to 12 at the start of a line
    (`1. `, `2. `, ...), as in design section 4. In each agent file, the line
    `## Common rules` is followed by one blank line, and everything after
    that blank line, to the end of the file, equals common.md byte for byte.
11. Product Manager. product-manager.md has no frontmatter: its first line is
    not `---`. Its only headings that start with a task ID are
    `### PM1 Requirements` to `### PM5 Status`, in order and as in design
    section 6.1, each with text under it. It holds the Product Manager's Must
    not cell from requirements section 4 (whitespace collapsed, as in 8). It
    does not use `${CLAUDE_PLUGIN_ROOT}`, which Claude Code replaces only in
    agent, skill, and command content (design section 4).

Run from the repository root:
python3 -m unittest discover -s troy-mode/dev/tests -v
"""

import codecs
import functools
import re
import unittest
from pathlib import Path
from typing import NamedTuple, Optional

REPO = Path(__file__).resolve().parents[3]
AGENTS = REPO / "agents"
ROLES_DIR = REPO / "troy-mode" / "roles"
COMMON = ROLES_DIR / "common.md"
PRODUCT_MANAGER = ROLES_DIR / "product-manager.md"
REQUIREMENTS = REPO / "docs" / "troy-mode" / "requirements.md"

# ---------------------------------------------------------------------------
# Expected values, from the F04 design, version 1.0.
# ---------------------------------------------------------------------------

PATTERN = "pattern"
CLASS = "class"

# The five path classes of F02 design section 5.
PATH_CLASSES = ("config", "dependencies", "tests", "docs", "source")

# The body sections of design section 7, in order.
BODY_SECTIONS = ("Who you are", "Must not", "Write scope", "Tasks", "Report", "Common rules")

# The report fields of design section 5.2, in order.
REPORT_FIELDS = ("Role", "Task", "Result", "Changed files", "Checks", "Summary", "Findings",
                 "Question")

# The only frontmatter fields an agent sets (design section 7).
FRONTMATTER_KEYS = ("name", "description", "tools", "model")

# What every description says (design 10.1, D34).
DESCRIPTION_PHRASE = "started only by the troy-mode entry skill"

# The results of design section 5.2, in the order of its Result line.
RESULT_ORDER = ("done", "failed", "approved", "changes-requested", "needs-answer", "escalate")

# Results each role sends. Design section 5.2's "Sent by" column gives done
# and failed to authors, approved and changes-requested to reviewers, and
# needs-answer and escalate to any role. A role is an author when its "Owns"
# line in design section 6 names something, and a reviewer when its
# "Reviews" line does:
#
#   Role                Owns (6.x)                 Reviews (6.x)              Sends
#   Architect           architecture, ADRs, ...    each interface design      all six
#   Interface Designer  external interface design  nothing                    author + any
#   Test Manager        test plans, triage         each test PR               all six
#   Developer           mock, impl, bug fix PRs    nothing                    author + any
#   Test Engineer       test code                  nothing                    author + any
#   Code Reviewer       nothing                    mock, test, impl, ... PRs  reviewer + any
#
# Each list keeps the order of RESULT_ORDER.
RESULTS = {
    "Architect": ("done", "failed", "approved", "changes-requested", "needs-answer", "escalate"),
    "Interface Designer": ("done", "failed", "needs-answer", "escalate"),
    "Test Manager": ("done", "failed", "approved", "changes-requested", "needs-answer",
                     "escalate"),
    "Developer": ("done", "failed", "needs-answer", "escalate"),
    "Test Engineer": ("done", "failed", "needs-answer", "escalate"),
    "Code Reviewer": ("approved", "changes-requested", "needs-answer", "escalate"),
}


class Role(NamedTuple):
    """One subagent role as the F04 design defines it.

    Attributes:
        name: The role's name, as in design section 3 and requirements section 4.
        stem: The agent file's name without `.md` (requirements Q4).
        model: The frontmatter model (design section 3, Q3).
        tools: The frontmatter tools, in order (design section 3, D30).
        tasks: The (ID, title) pairs of the role's tasks, in order (design section 6).
        results: The results the role sends (RESULTS).
        scope: The (PATTERN or CLASS, value) pairs of the write scope (design section 3, D31).
    """

    name: str
    stem: str
    model: str
    tools: tuple[str, ...]
    tasks: tuple[tuple[str, str], ...]
    results: tuple[str, ...]
    scope: tuple[tuple[str, str], ...]


AGENT_ROLES = (
    Role(name="Architect", stem="troy-architect", model="opus",
         tools=("Read", "Grep", "Glob", "Write", "Edit", "Bash", "WebSearch", "WebFetch"),
         tasks=(("AR1", "Architecture"), ("AR2", "Design review"),
                ("AR3", "Dependency review"), ("AR4", "Change impact"), ("AR5", "Answer")),
         results=RESULTS["Architect"],
         scope=((PATTERN, "docs/architecture*.md"), (PATTERN, "docs/adr/**"),
                (PATTERN, "docs/features/*/design*.md"))),
    Role(name="Interface Designer", stem="troy-interface-designer", model="opus",
         tools=("Read", "Grep", "Glob", "Write", "Edit"),
         tasks=(("IF1", "Design"), ("IF2", "Revise"), ("IF3", "Answer"),
                ("IF4", "Coverage ruling")),
         results=RESULTS["Interface Designer"],
         scope=((PATTERN, "docs/features/*/design*.md"),)),
    Role(name="Test Manager", stem="troy-test-manager", model="opus",
         tools=("Read", "Grep", "Glob", "Write", "Edit", "Bash"),
         tasks=(("TM1", "Test plan"), ("TM2", "Test review"), ("TM3", "Coverage gap"),
                ("TM4", "Disputed test"), ("TM5", "Bug triage"), ("TM6", "Exclusion"),
                ("TM7", "Version test plan")),
         results=RESULTS["Test Manager"],
         scope=((PATTERN, "docs/features/*/test-plan*.md"),
                (PATTERN, "docs/versions/*/test-plan*.md"))),
    Role(name="Developer", stem="troy-developer", model="sonnet",
         tools=("Read", "Grep", "Glob", "Write", "Edit", "Bash"),
         tasks=(("DV1", "Mock"), ("DV2", "Implementation"), ("DV3", "Bug fix"),
                ("DV4", "Delete")),
         results=RESULTS["Developer"],
         scope=((CLASS, "source"), (CLASS, "dependencies"))),
    # TE5 "Version tests" is F08's (F08 design section 9, interface note 13).
    Role(name="Test Engineer", stem="troy-test-engineer", model="sonnet",
         tools=("Read", "Grep", "Glob", "Write", "Edit", "Bash"),
         tasks=(("TE1", "Tests"), ("TE2", "Reproduction test"), ("TE3", "Test fix"),
                ("TE4", "Added cases"), ("TE5", "Version tests")),
         results=RESULTS["Test Engineer"],
         scope=((CLASS, "tests"), (CLASS, "dependencies"))),
    Role(name="Code Reviewer", stem="troy-code-reviewer", model="opus",
         tools=("Read", "Grep", "Glob", "Bash", "Skill"),
         tasks=(("CR1", "Review"),),
         results=RESULTS["Code Reviewer"],
         scope=()),
)

PM_NAME = "Product Manager"
PM_TASKS = (("PM1", "Requirements"), ("PM2", "Change request"), ("PM3", "Acceptance"),
            ("PM4", "Version"), ("PM5", "Status"))

# Every role in the requirements section 4 table.
REQUIREMENT_ROLES = (PM_NAME,) + tuple(role.name for role in AGENT_ROLES)

# D37: the pattern the Architect and the Interface Designer split by section.
D37_PATTERN = "docs/features/*/design*.md"

COMMON_RULE_COUNT = 12  # design section 4
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"

# ---------------------------------------------------------------------------
# Markdown parsing.
# ---------------------------------------------------------------------------

HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*$")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
TASK_ID = re.compile(r"^[A-Z]{2}\d+\b")
FRONT_LINE = re.compile(r"^([A-Za-z][\w-]*):[ \t]+(\S.*?)[ \t]*$")
REPORT_LINE = re.compile(r"^([A-Z][A-Za-z ]*?): ?(.*)$")
BACKTICKED = re.compile(r"`([^`]+)`")
RULE_NUMBER = re.compile(r"^(\d+)\. \S")
SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


class Line(NamedTuple):
    """One line of a Markdown file.

    Attributes:
        number: The line's number in the file, from 1.
        text: The line without its newline.
        fence: True for a line that opens or closes a fenced code block.
        code: True for a line inside a fenced code block.
    """

    number: int
    text: str
    fence: bool
    code: bool

    def heading(self) -> Optional[tuple[int, str]]:
        """Returns the line's heading level and title, or None if it is not a heading."""
        if self.fence or self.code:
            return None
        match = HEADING.match(self.text)
        return (len(match.group(1)), match.group(2)) if match else None


def scan(lines: list[str], first: int = 1) -> list[Line]:
    """Marks which lines open, close, or sit inside fenced code blocks.

    Args:
        lines: The lines, without newlines.
        first: The file line number of the first line.

    Returns:
        One Line per input line.
    """
    found, fence = [], None
    for number, text in enumerate(lines, start=first):
        if fence is None:
            match = FENCE_OPEN.match(text)
            if match:
                fence = re.compile(r"^ {0,3}" + re.escape(match.group(1)[0])
                                   + "{" + str(len(match.group(1))) + r",}[ \t]*$")
            found.append(Line(number, text, fence=bool(match), code=False))
        elif fence.match(text):
            fence = None
            found.append(Line(number, text, fence=True, code=False))
        else:
            found.append(Line(number, text, fence=False, code=True))
    return found


class Markdown:
    """A Markdown file split into its frontmatter and its scanned body.

    Attributes:
        opened: True when the first line is `---`.
        frontmatter: The lines between the first line and the next `---` line,
            or None when the file has no closed frontmatter.
        body: The scanned lines after the frontmatter, or every line when
            there is none.
    """

    def __init__(self, text: str) -> None:
        """Splits the text.

        Args:
            text: The file's text.
        """
        lines = text.split("\n")
        self.opened = lines[0] == "---"
        self.frontmatter: Optional[list[str]] = None
        start = 0
        if self.opened and "---" in lines[1:]:
            end = lines.index("---", 1)
            self.frontmatter = lines[1:end]
            start = end + 1
        self.body = scan(lines[start:], start + 1)

    def headings(self) -> list[tuple[int, str]]:
        """Returns the (level, title) of every heading in the body, in order."""
        return [heading for heading in (line.heading() for line in self.body) if heading]

    def sections(self) -> dict[str, list[Line]]:
        """Maps each level-2 title to its lines, up to the next level-1 or 2 heading.

        When a title repeats, the first section keeps it.
        """
        found: dict[str, list[Line]] = {}
        current: Optional[list[Line]] = None
        for line in self.body:
            heading = line.heading()
            if heading and heading[0] <= 2:
                current = None
                if heading[0] == 2 and heading[1] not in found:
                    current = found[heading[1]] = []
            elif current is not None:
                current.append(line)
        return found


def subsections(lines: list[Line], level: int) -> list[tuple[str, list[Line]]]:
    """Splits lines at the headings of one level.

    Args:
        lines: Scanned lines.
        level: The heading level to split at.

    Returns:
        The (title, lines) of each subsection, in order. A subsection runs to
        the next heading of that level or a higher one. Lines before the
        first such heading are left out.
    """
    found: list[tuple[str, list[Line]]] = []
    current: Optional[list[Line]] = None
    for line in lines:
        heading = line.heading()
        if heading and heading[0] <= level:
            current = None
            if heading[0] == level:
                current = []
                found.append((heading[1], current))
        elif current is not None:
            current.append(line)
    return found


def has_text(lines: list[Line]) -> bool:
    """Tells whether any line that is not a heading has text."""
    return any(line.text.strip() and not line.heading() for line in lines)


def code_blocks(lines: list[Line]) -> list[list[str]]:
    """Returns the content lines of each fenced code block, in order."""
    blocks: list[list[str]] = []
    current: Optional[list[str]] = None
    for line in lines:
        if line.fence:
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif line.code and current is not None:
            current.append(line.text)
    if current is not None:
        blocks.append(current)
    return blocks


def normalize(text: str) -> str:
    """Collapses each run of whitespace to one space and trims the ends."""
    return " ".join(text.split())


@functools.lru_cache(maxsize=None)
def requirement_must_nots() -> tuple[tuple[tuple[str, str], ...], str]:
    """Reads the Role and Must not columns of the roles table in requirements section 4.

    Returns:
        The (role, normalized Must not cell) pairs, and a problem that stops
        the table from being read, or "" when there is none.
    """
    if not REQUIREMENTS.is_file():
        return (), "the file is missing"
    rows, seen, inside = [], False, False
    for line in scan(REQUIREMENTS.read_text(encoding="utf-8").split("\n")):
        heading = line.heading()
        if heading:
            if inside:
                break
            inside = heading[0] == 2 and re.match(r"^4\.\s+Roles$", heading[1]) is not None
            seen = seen or inside
        elif inside and not line.code and line.text.strip().startswith("|"):
            rows.append([cell.strip() for cell in line.text.strip().strip("|").split("|")])
    if not seen:
        return (), "has no '## 4. Roles' section"
    if len(rows) < 3 or not all(SEPARATOR_CELL.match(cell) for cell in rows[1]):
        return (), "section 4 has no roles table with at least one row"
    header = rows[0]
    if "Role" not in header or "Must not" not in header:
        return (), f"the section 4 table has no Role or Must not column: {header}"
    pairs = []
    for cells in rows[2:]:
        if len(cells) != len(header):
            return (), f"a section 4 table row has {len(cells)} cells, not {len(header)}: {cells}"
        pairs.append((cells[header.index("Role")], normalize(cells[header.index("Must not")])))
    return tuple(pairs), ""


def first_difference(expected: bytes, found: bytes, first_line: int) -> str:
    """Describes where a copy of common.md first differs from it.

    Args:
        expected: common.md's bytes.
        found: The copy's bytes.
        first_line: The agent file's line number of the copy's first line.

    Returns:
        A sentence naming the first differing line.
    """
    want, got = expected.split(b"\n"), found.split(b"\n")
    for offset, (a, b) in enumerate(zip(want, got)):
        if a != b:
            return (f"first difference at common.md line {offset + 1} (agent line "
                    f"{first_line + offset}): expected {a.decode('utf-8', 'replace')!r}, "
                    f"found {b.decode('utf-8', 'replace')!r}")
    return f"common.md has {len(want)} lines and the copy has {len(got)}"


def where(role: Role) -> str:
    """Names an agent file and its role for failure messages."""
    return f"agents/{role.stem}.md ({role.name})"


PM_WHERE = f"troy-mode/roles/product-manager.md ({PM_NAME})"
COMMON_WHERE = "troy-mode/roles/common.md (the six subagent roles)"
REQUIREMENTS_WHERE = "docs/troy-mode/requirements.md (roles table, section 4)"

# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class RoleFileCase(unittest.TestCase):
    """Shared helpers that fail the test, naming the file and the role, when a part is missing."""

    maxDiff = None

    def agent_roles(self) -> tuple[Role, ...]:
        """Returns the expected roles, failing if the table is not the six roles."""
        self.assertEqual(6, len(AGENT_ROLES), "test_roles.py: AGENT_ROLES must list six roles")
        return AGENT_ROLES

    def read(self, path: Path, who: str) -> tuple[bytes, str]:
        """Reads a file as bytes and as UTF-8 text.

        Args:
            path: The file.
            who: The file and role, for failure messages.

        Returns:
            The bytes and the text.
        """
        if not path.is_file():
            self.fail(f"{who}: the file is missing")
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            self.fail(f"{who}: the file is not UTF-8: {error}")
        self.assertTrue(text.strip(), f"{who}: the file is empty")
        return data, text

    def agent(self, role: Role) -> tuple[bytes, str, Markdown]:
        """Reads an agent file and parses it."""
        data, text = self.read(AGENTS / f"{role.stem}.md", where(role))
        return data, text, Markdown(text)

    def section(self, role: Role, title: str) -> list[Line]:
        """Returns an agent file's level-2 section, failing if it is missing or empty."""
        sections = self.agent(role)[2].sections()
        self.assertIn(title, sections, f"{where(role)}: has no '## {title}' section")
        self.assertTrue(has_text(sections[title]), f"{where(role)}: '## {title}' is empty")
        return sections[title]

    def must_not(self, name: str, who: str) -> str:
        """Returns a role's normalized Must not cell from requirements section 4."""
        pairs, problem = requirement_must_nots()
        self.assertEqual("", problem, f"{REQUIREMENTS_WHERE}, needed by {who}: {problem}")
        cells = [cell for role, cell in pairs if role == name]
        self.assertEqual(1, len(cells),
                         f"{REQUIREMENTS_WHERE}, needed by {who}: expected one row for {name}")
        self.assertTrue(cells[0], f"{REQUIREMENTS_WHERE}, needed by {who}: Must not is empty")
        return cells[0]

    def common_bytes(self) -> bytes:
        """Returns common.md's bytes, failing if it is missing or empty."""
        return self.read(COMMON, COMMON_WHERE)[0]


class ExpectedTableTests(RoleFileCase):
    """The expected tables in this file are complete, so no test passes on an empty table."""

    def test_expected_tables_are_complete(self) -> None:
        """Six roles with every value set, and only the Code Reviewer's scope empty."""
        roles = self.agent_roles()
        self.assertEqual(len(roles), len({role.name for role in roles}), "test_roles.py: names")
        self.assertEqual(len(roles), len({role.stem for role in roles}), "test_roles.py: stems")
        self.assertEqual({role.name for role in roles}, set(RESULTS), "test_roles.py: RESULTS")
        for role in roles:
            with self.subTest(role=role.name):
                self.assertIn(role.model, ("opus", "sonnet"), f"test_roles.py: {role.name}")
                self.assertTrue(role.tools, f"test_roles.py: {role.name} has no tools")
                self.assertTrue(role.tasks, f"test_roles.py: {role.name} has no tasks")
                self.assertTrue(role.results, f"test_roles.py: {role.name} has no results")
                self.assertEqual([r for r in RESULT_ORDER if r in role.results],
                                 list(role.results), f"test_roles.py: {role.name} results")
                for kind, value in role.scope:
                    self.assertIn(kind, (PATTERN, CLASS), f"test_roles.py: {role.name} scope")
                    if kind == CLASS:
                        self.assertIn(value, PATH_CLASSES, f"test_roles.py: {role.name} scope")
        self.assertEqual(["Code Reviewer"], [role.name for role in roles if not role.scope],
                         "test_roles.py: only the Code Reviewer has an empty write scope")
        for table in (PM_TASKS, PATH_CLASSES, BODY_SECTIONS, REPORT_FIELDS, FRONTMATTER_KEYS,
                      RESULT_ORDER):
            self.assertTrue(table, "test_roles.py: an expected table is empty")
        self.assertEqual(7, len(REQUIREMENT_ROLES), "test_roles.py: REQUIREMENT_ROLES")


class FileTests(RoleFileCase):
    """Files group: the role files exist where design section 2 puts them."""

    def test_agents_folder_holds_exactly_the_six_role_files(self) -> None:
        """agents/ has the six troy-* files of requirements Q4 and no other troy-* entry."""
        expected = {f"{role.stem}.md" for role in self.agent_roles()}
        found = {path.name for path in AGENTS.glob("troy-*")} if AGENTS.is_dir() else set()
        self.assertEqual(expected, found,
                         "agents/: the troy-* entries must be exactly the six role files ("
                         + ", ".join(role.name for role in AGENT_ROLES) + ")")

    def test_each_agent_file_exists(self) -> None:
        """Each role's agent file is a file."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertTrue((AGENTS / f"{role.stem}.md").is_file(),
                                f"{where(role)}: the file is missing")

    def test_roles_folder_holds_common_and_product_manager(self) -> None:
        """troy-mode/roles/ has common.md and product-manager.md and nothing else (D35)."""
        self.assertTrue(ROLES_DIR.is_dir(),
                        f"troy-mode/roles/ ({PM_NAME} and the shared rules): folder is missing")
        found = {path.name for path in ROLES_DIR.iterdir()}
        self.assertEqual({"common.md", "product-manager.md"}, found,
                         f"troy-mode/roles/ ({PM_NAME} and the shared rules): wrong files")
        for path, who in ((COMMON, COMMON_WHERE), (PRODUCT_MANAGER, PM_WHERE)):
            with self.subTest(file=path.name):
                self.assertTrue(path.is_file(), f"{who}: the file is missing")

    def test_role_files_are_utf8_with_lf_line_endings(self) -> None:
        """Every role file is non-empty UTF-8 with no byte order mark and no CR."""
        files = [(AGENTS / f"{role.stem}.md", where(role)) for role in self.agent_roles()]
        files += [(COMMON, COMMON_WHERE), (PRODUCT_MANAGER, PM_WHERE)]
        for path, who in files:
            with self.subTest(file=who):
                data, _ = self.read(path, who)
                self.assertFalse(data.startswith(codecs.BOM_UTF8), f"{who}: has a byte order mark")
                self.assertNotIn(b"\r", data, f"{who}: must use LF line endings")


class FrontmatterTests(RoleFileCase):
    """Frontmatter group: each agent's frontmatter is as design sections 3 and 7 say."""

    def fields(self, role: Role) -> dict[str, str]:
        """Parses an agent file's frontmatter, failing the test when it does not parse."""
        doc = self.agent(role)[2]
        self.assertTrue(doc.opened, f"{where(role)}: the first line must be ---")
        self.assertIsNotNone(doc.frontmatter, f"{where(role)}: frontmatter has no closing ---")
        self.assertTrue(doc.frontmatter, f"{where(role)}: the frontmatter is empty")
        found: dict[str, str] = {}
        for number, line in enumerate(doc.frontmatter, start=2):
            match = FRONT_LINE.match(line)
            self.assertIsNotNone(match, f"{where(role)}: frontmatter line {number} is not "
                                        f"'key: value': {line!r}")
            key, value = match.group(1), match.group(2)
            self.assertNotIn(key, found, f"{where(role)}: frontmatter repeats {key}")
            found[key] = value
        return found

    def field(self, role: Role, key: str) -> str:
        """Returns one frontmatter value, failing if it is missing."""
        fields = self.fields(role)
        self.assertIn(key, fields, f"{where(role)}: the frontmatter has no {key}")
        return fields[key]

    def test_frontmatter_parses(self) -> None:
        """The frontmatter is `---`, `key: value` lines, and `---`."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertTrue(self.fields(role), f"{where(role)}: no frontmatter fields")

    def test_only_name_description_tools_and_model(self) -> None:
        """No field other than name, description, tools, and model, and all four set."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertEqual(sorted(FRONTMATTER_KEYS), sorted(self.fields(role)),
                                 f"{where(role)}: wrong frontmatter fields")

    def test_name_equals_file_name(self) -> None:
        """name is the file name without .md."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertEqual(role.stem, self.field(role, "name"), f"{where(role)}: name")

    def test_description_says_only_the_entry_skill_starts_the_role(self) -> None:
        """description names the role and says only the troy-mode entry skill starts it (D34)."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                description = self.field(role, "description")
                self.assertIn(DESCRIPTION_PHRASE, description.lower(),
                              f"{where(role)}: description must say '{DESCRIPTION_PHRASE}'")
                self.assertIn(role.name, description,
                              f"{where(role)}: description must name the role")

    def test_model_equals_design(self) -> None:
        """model is the role's model in design section 3 (Q3)."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertEqual(role.model, self.field(role, "model"), f"{where(role)}: model")

    def test_tools_equal_design(self) -> None:
        """tools is exactly the role's list in design section 3, in order (D30)."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                tools = [tool.strip() for tool in self.field(role, "tools").split(",")]
                self.assertEqual(list(role.tools), tools, f"{where(role)}: tools")


class BodyTests(RoleFileCase):
    """Body group: headings, tasks, and report as design sections 5.2, 6, and 7 say."""

    def report_lines(self, role: Role) -> list[tuple[str, str]]:
        """Returns the (field, value) lines of the Report section's one code block."""
        blocks = code_blocks(self.section(role, "Report"))
        self.assertEqual(1, len(blocks),
                         f"{where(role)}: '## Report' must hold exactly one fenced code block")
        lines = [text for text in blocks[0] if text.strip()]
        self.assertTrue(lines, f"{where(role)}: the report code block is empty")
        found = []
        for text in lines:
            match = REPORT_LINE.match(text)
            self.assertIsNotNone(match, f"{where(role)}: report line is not 'Field: value': "
                                        f"{text!r}")
            found.append((match.group(1), match.group(2).strip()))
        return found

    def test_headings_are_the_role_name_and_the_six_sections_in_order(self) -> None:
        """The level-1 and level-2 headings are `# <Role>` and the six of section 7."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                doc = self.agent(role)[2]
                expected = [(1, role.name)] + [(2, title) for title in BODY_SECTIONS]
                found = [heading for heading in doc.headings() if heading[0] <= 2]
                self.assertEqual(expected, found,
                                 f"{where(role)}: level-1 and level-2 headings")

    def test_each_section_has_text(self) -> None:
        """None of the six sections is empty."""
        for role in self.agent_roles():
            for title in BODY_SECTIONS:
                with self.subTest(role=role.name, section=title):
                    self.section(role, title)

    def test_task_subsections_equal_design_section_6(self) -> None:
        """The level-3 headings under Tasks are the role's tasks, in order, and nothing else."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                expected = [f"{task_id} {title}" for task_id, title in role.tasks]
                self.assertTrue(expected, f"test_roles.py: {role.name} has no tasks")
                found = [title for title, _ in subsections(self.section(role, "Tasks"), 3)]
                self.assertEqual(expected, found, f"{where(role)}: task headings under Tasks")

    def test_each_task_has_steps(self) -> None:
        """Each task subsection has text under its heading."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                tasks = subsections(self.section(role, "Tasks"), 3)
                self.assertTrue(tasks, f"{where(role)}: '## Tasks' has no task subsections")
                for title, lines in tasks:
                    self.assertTrue(has_text(lines), f"{where(role)}: task '{title}' is empty")

    def test_task_ids_head_only_the_task_subsections(self) -> None:
        """No heading outside the task subsections starts with a task ID."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                expected = [(3, f"{task_id} {title}") for task_id, title in role.tasks]
                self.assertTrue(expected, f"test_roles.py: {role.name} has no tasks")
                found = [heading for heading in self.agent(role)[2].headings()
                         if TASK_ID.match(heading[1])]
                self.assertEqual(expected, found, f"{where(role)}: headings with task IDs")

    def test_report_has_the_fields_of_design_section_5_2(self) -> None:
        """The report block's fields are those of section 5.2, in order."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                names = [name for name, _ in self.report_lines(role)]
                self.assertEqual(list(REPORT_FIELDS), names, f"{where(role)}: report fields")

    def test_report_lists_exactly_the_results_the_role_sends(self) -> None:
        """The Result line lists the role's results from RESULTS, separated by ' | '."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertTrue(role.results, f"test_roles.py: {role.name} has no results")
                values = [value for name, value in self.report_lines(role) if name == "Result"]
                self.assertEqual(1, len(values), f"{where(role)}: needs one Result line")
                found = [result.strip() for result in values[0].split(" | ")]
                self.assertEqual(list(role.results), found, f"{where(role)}: Result line")


class MustNotTests(RoleFileCase):
    """Must not group: each agent holds its line from requirements section 4."""

    def test_requirements_table_lists_the_seven_roles(self) -> None:
        """The requirements section 4 table has a row with a Must not cell for each role."""
        pairs, problem = requirement_must_nots()
        self.assertEqual("", problem, f"{REQUIREMENTS_WHERE}: {problem}")
        self.assertEqual(sorted(REQUIREMENT_ROLES), sorted(role for role, _ in pairs),
                         f"{REQUIREMENTS_WHERE}: the rows must be the seven roles")
        for role, cell in pairs:
            with self.subTest(role=role):
                self.assertTrue(cell, f"{REQUIREMENTS_WHERE}: {role}'s Must not cell is empty")

    def test_must_not_section_holds_the_requirements_line(self) -> None:
        """Each agent's Must not section contains its requirements line."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                expected = self.must_not(role.name, where(role))
                text = normalize("\n".join(line.text for line in self.section(role, "Must not")))
                self.assertIn(expected, text, f"{where(role)}: '## Must not' lacks the "
                                              f"requirements section 4 line {expected!r}")


class WriteScopeTests(RoleFileCase):
    """Write scope group: each agent's scope is the set in design section 3 (D31)."""

    def bullets(self, role: Role) -> list[str]:
        """Returns the Write scope section's non-blank lines, failing if one is not a bullet."""
        lines = [line.text.rstrip() for line in self.section(role, "Write scope")
                 if line.text.strip()]
        for text in lines:
            self.assertTrue(text.startswith("- "),
                            f"{where(role)}: Write scope line is not a '- ' bullet: {text!r}")
        return lines

    def items(self, role: Role) -> list[tuple[str, str]]:
        """Parses the Write scope bullets into (PATTERN or CLASS, value) pairs."""
        bullets = self.bullets(role)
        if bullets == ["- None"]:
            return []
        found = []
        for text in bullets:
            match = BACKTICKED.search(text)
            self.assertIsNotNone(match, f"{where(role)}: Write scope bullet names no backticked "
                                        f"pattern or class (an empty scope is the one line "
                                        f"'- None'): {text!r}")
            if "path class" in text:
                self.assertIn(match.group(1), PATH_CLASSES,
                              f"{where(role)}: not one of F02's path classes: {text!r}")
                found.append((CLASS, match.group(1)))
            else:
                found.append((PATTERN, match.group(1)))
        return found

    def test_every_line_is_a_bullet(self) -> None:
        """Each non-blank line of Write scope is a '- ' bullet."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertTrue(self.bullets(role), f"{where(role)}: Write scope is empty")

    def test_write_scope_equals_design_section_3(self) -> None:
        """The patterns and classes, or None, are exactly the role's scope in section 3."""
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                self.assertEqual(sorted(role.scope), sorted(self.items(role)),
                                 f"{where(role)}: write scope")

    def test_architect_and_interface_designer_split_the_design_by_section(self) -> None:
        """D37: the Architect writes section 4 of a design, the Interface Designer the rest."""
        cases = (("troy-architect", "section 4", "except section 4"),
                 ("troy-interface-designer", "except section 4", None))
        for stem, required, forbidden in cases:
            roles = [role for role in self.agent_roles() if role.stem == stem]
            self.assertEqual(1, len(roles), f"test_roles.py: no role {stem}")
            role = roles[0]
            with self.subTest(role=role.name):
                lines = [text for text in self.bullets(role)
                         if (match := BACKTICKED.search(text)) and match.group(1) == D37_PATTERN]
                self.assertEqual(1, len(lines), f"{where(role)}: needs one `{D37_PATTERN}` bullet")
                self.assertIn(required, lines[0], f"{where(role)}: the `{D37_PATTERN}` bullet "
                                                  f"must say '{required}' (D37)")
                if forbidden:
                    self.assertNotIn(forbidden, lines[0], f"{where(role)}: the `{D37_PATTERN}` "
                                                          f"bullet must not say '{forbidden}'")


class CommonRulesTests(RoleFileCase):
    """Common rules group: common.md holds the shared rules, and each agent copies it (D28)."""

    def test_common_md_has_no_level_1_or_level_2_headings(self) -> None:
        """common.md sits under each agent's '## Common rules', so it starts no section."""
        _, text = self.read(COMMON, COMMON_WHERE)
        headings = [heading for heading in Markdown(text).headings() if heading[0] <= 2]
        self.assertEqual([], headings, f"{COMMON_WHERE}: level-1 or level-2 headings")

    def test_common_md_numbers_rules_1_to_12(self) -> None:
        """common.md holds the twelve numbered rules of design section 4, in order."""
        _, text = self.read(COMMON, COMMON_WHERE)
        numbers = [int(match.group(1)) for line in scan(text.split("\n"))
                   if not line.code and not line.fence and (match := RULE_NUMBER.match(line.text))]
        self.assertEqual(list(range(1, COMMON_RULE_COUNT + 1)), numbers,
                         f"{COMMON_WHERE}: rule numbers")

    def test_each_agent_ends_with_an_exact_copy_of_common_md(self) -> None:
        """After '## Common rules' and one blank line, the rest equals common.md byte for byte."""
        common = self.common_bytes()
        for role in self.agent_roles():
            with self.subTest(role=role.name):
                data, text, doc = self.agent(role)
                headings = [line for line in doc.body if line.heading() == (2, "Common rules")]
                self.assertEqual(1, len(headings), f"{where(role)}: needs one '## Common rules'")
                number = headings[0].number
                lines = text.split("\n")
                self.assertLess(number + 1, len(lines),
                                f"{where(role)}: nothing follows '## Common rules'")
                self.assertEqual("", lines[number].strip(),
                                 f"{where(role)}: '## Common rules' must be followed by a blank "
                                 f"line")
                copy = data[len(("\n".join(lines[:number + 1]) + "\n").encode("utf-8")):]
                if copy != common:
                    self.fail(f"{where(role)}: the Common rules section differs from "
                              f"troy-mode/roles/common.md: "
                              f"{first_difference(common, copy, number + 2)}")


class ProductManagerTests(RoleFileCase):
    """Product Manager group: product-manager.md holds tasks PM1 to PM5 and the Must not line."""

    def doc(self) -> tuple[str, Markdown]:
        """Reads product-manager.md and parses it."""
        _, text = self.read(PRODUCT_MANAGER, PM_WHERE)
        return text, Markdown(text)

    def test_has_no_frontmatter(self) -> None:
        """The main session reads the file, so it is not an agent and has no frontmatter."""
        text, _ = self.doc()
        self.assertNotEqual("---", text.split("\n")[0], f"{PM_WHERE}: must have no frontmatter")

    def test_task_headings_are_pm1_to_pm5(self) -> None:
        """The only headings with task IDs are PM1 to PM5 of design section 6.1, in order."""
        self.assertEqual(5, len(PM_TASKS), "test_roles.py: PM_TASKS")
        expected = [(3, f"{task_id} {title}") for task_id, title in PM_TASKS]
        found = [heading for heading in self.doc()[1].headings() if TASK_ID.match(heading[1])]
        self.assertEqual(expected, found, f"{PM_WHERE}: headings with task IDs")

    def test_each_task_has_steps(self) -> None:
        """Each PM task heading has text under it."""
        tasks = dict(subsections(self.doc()[1].body, 3))
        for task_id, title in PM_TASKS:
            with self.subTest(task=task_id):
                heading = f"{task_id} {title}"
                self.assertIn(heading, tasks, f"{PM_WHERE}: no '### {heading}'")
                self.assertTrue(has_text(tasks[heading]), f"{PM_WHERE}: task {task_id} is empty")

    def test_holds_the_must_not_line(self) -> None:
        """The file contains the Product Manager's Must not line from requirements section 4."""
        line = self.must_not(PM_NAME, PM_WHERE)
        self.assertIn(line, normalize(self.doc()[0]),
                      f"{PM_WHERE}: lacks the requirements section 4 Must not line {line!r}")

    def test_does_not_use_the_plugin_root_variable(self) -> None:
        """Claude Code does not replace ${CLAUDE_PLUGIN_ROOT} in a file read with Read."""
        self.assertNotIn(PLUGIN_ROOT, self.doc()[0],
                         f"{PM_WHERE}: name plugin files by relative paths, not {PLUGIN_ROOT}")


if __name__ == "__main__":
    unittest.main()
