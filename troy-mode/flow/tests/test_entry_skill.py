"""Skill group (F07 design 2, 4, 8.1, 14.1): ``skills/troy-mode/SKILL.md``."""

import re
import unittest

from flow_helpers import PLUGIN_ROOT

SKILL = PLUGIN_ROOT / "skills/troy-mode/SKILL.md"
ENGINE_PATH = "${CLAUDE_PLUGIN_ROOT}/troy-mode/flow/troy_flow.py"
PM_PATH = "${CLAUDE_PLUGIN_ROOT}/troy-mode/roles/product-manager.md"
COMMANDS = ("status", "brief", "snapshot", "check-run", "approve", "check-text", "check-skips",
            "series", "wait-checks")
FLOWS = ("Project setup", "Feature loop", "Bug fix", "Requirement change",
         "Work outside the pipeline", "Continue", "Upgrade", "Version release", "Rule change")
STAGE_TITLES = ("[<ID> 1/6 design] <name>", "[<ID> 2/6 test-plan] <name>",
                "[<ID> 3/6 mock] <name>", "[<ID> 4/6 tests] <name>", "[<ID> 5/6 impl] <name>",
                "[<ID> 6/6 accept] <name>")
WAIT_TEXT = "troy_flow.py wait-checks --pr <number> --sha <sha>"
MERGE_TEXT = "gh pr merge <number> --rebase --delete-branch --match-head-commit <sha>"
OLD_WAIT_TEXT = "gh pr checks <number> --watch"
GIT_TEXTS = ("git switch --detach", MERGE_TEXT, WAIT_TEXT, "git fetch origin")
PART2_TITLES = ("[B<n> A/B test] <summary>", "[B<n> B/B fix] <summary>",
                "[<ID> test-fix] <summary>", "[docs] Change the requirements: <summary>")
PART2_TEXTS = ("Fixes #<n>", "gh issue create", "--label bug", "gh pr close",
               "--allow-dependency")


def split_skill(text: str) -> tuple:
    """Splits SKILL.md into its front matter fields and the text after it.

    Args:
        text: The whole file.

    Returns:
        A dict of the top-level front matter keys and the body text.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        return {}, text
    end = lines.index("---", 1)
    fields = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip().strip("\"'")
    return fields, "\n".join(lines[end + 1:])


class EntrySkillTests(unittest.TestCase):
    """The skill Troy types for all work in a troy-mode project."""

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once; an empty text when it does not exist yet."""
        cls.text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.fields, cls.body = split_skill(cls.text)

    def test_front_matter_names_troy_mode(self):
        """The front matter's name is troy-mode."""
        self.assertEqual(self.fields.get("name"), "troy-mode")

    def test_runs_only_when_troy_types_it(self):
        """``disable-model-invocation: true`` (requirements section 8)."""
        self.assertEqual(self.fields.get("disable-model-invocation"), "true")

    def test_has_a_description(self):
        """The front matter has a description that is not empty."""
        self.assertNotEqual(self.fields.get("description", ""), "")

    def test_names_the_engine_and_the_product_manager(self):
        """The engine and the Product Manager's instructions by their plugin paths (design 2)."""
        for text in (ENGINE_PATH, PM_PATH):
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_names_every_engine_command(self):
        """Each command of design 3.1 as ``troy_flow.py <command>``."""
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assertRegex(self.body, re.escape(f"troy_flow.py {command}") + r"(?![\w-])")

    def test_names_every_flow(self):
        """Each flow of the routing table (design 4)."""
        for flow in FLOWS:
            with self.subTest(flow=flow):
                self.assertIn(flow, self.body)

    def test_names_the_six_stage_titles(self):
        """The PR titles of design 8.1."""
        for title in STAGE_TITLES:
            with self.subTest(title=title):
                self.assertIn(title, self.body)

    def test_names_the_merge_steps(self):
        """Detach, merge with the head check, wait for the checks with ``wait-checks`` (D204),
        and fetch (design 8.6)."""
        for text in GIT_TEXTS:
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_names_the_part_two_titles(self):
        """The bug, test-fix, and change PR titles (design 8.7, 11.1, 11.2)."""
        for title in PART2_TITLES:
            with self.subTest(title=title):
                self.assertIn(title, self.body)

    def test_names_the_part_two_commands(self):
        """The issue, the closing line, closing a stale PR, and allowing a dependency."""
        for text in PART2_TEXTS:
            with self.subTest(text=text):
                self.assertIn(text, self.body)

    def test_nothing_is_marked_not_built(self):
        """No line of the skill says ``not built`` (F09 note, section 10).

        F07 marked the version release and the rule change as not built yet.
        F08 built the version release and F09 builds the rule change, so no
        flow is left unbuilt.
        """
        self.assertNotEqual(self.body, "")
        lines = [line for line in self.body.split("\n") if "not built" in line.lower()]
        self.assertEqual(lines, [])

    def test_bug_fix_and_requirement_change_are_built(self):
        """No line about the bug fix or the requirement change says it is not built."""
        for line in self.body.split("\n"):
            lower = line.lower()
            if "bug fix" in lower or "requirement change" in lower:
                with self.subTest(line=line):
                    self.assertNotIn("not built", lower)

    def test_no_longer_part_one_of_two(self):
        """Part 2 completes the skill: it no longer says it is part 1 of 2."""
        self.assertNotEqual(self.body, "")
        self.assertNotIn("part 1 of 2", self.body.lower())


def routing_rows(body: str) -> list:
    """The routing table's rows, as lists of trimmed cells.

    Args:
        body: The skill's text after the front matter.

    Returns:
        The rows of the first table under ``## Routing``, header and separator left out.
    """
    lines = body.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Routing"), None)
    if start is None:
        return []
    rows = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.strip().startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return [row for row in rows[2:] if row]


class VersionReleaseSkillTests(unittest.TestCase):
    """F08's texts in the entry skill (F08 design 5, interface note section 12)."""

    COMMANDS = ("release-test", "accept-version", "release-notes", "retro")
    TITLES = ("[docs] Add the <version> test plan", "[<version> tests] <summary>",
              "[docs] Release <tag>", "[docs] Record Troy's acceptance of <tag>")
    HEADINGS = ("Release test, run <n>:", "Release test by Troy, run <n>:",
                "Waiting for Troy: accept <tag>", "Retrospective: <tag>",
                "Bug deferred by Troy: #<n>")

    @classmethod
    def setUpClass(cls):
        """Reads SKILL.md once; an empty text when it does not exist yet."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.body = split_skill(text)[1]

    def test_names_every_new_engine_command(self):
        """Each command of F08 design 3.1 as ``troy_flow.py <command>``."""
        for command in self.COMMANDS:
            with self.subTest(command=command):
                self.assertRegex(self.body, re.escape(f"troy_flow.py {command}") + r"(?![\w-])")

    def test_names_the_release_titles(self):
        """The test plan, version tests, release, and record titles."""
        for title in self.TITLES:
            with self.subTest(title=title):
                self.assertIn(title, self.body)

    def test_names_the_github_release_with_its_target(self):
        """``gh release create`` on one line with ``--target`` (D73)."""
        lines = [line for line in self.body.split("\n") if "gh release create" in line]
        self.assertTrue(any("--target" in line for line in lines), lines)

    def test_names_the_comment_headings(self):
        """F08's comment headings (design 5.5 to 5.8 and 7)."""
        for heading in self.HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, self.body)

    def test_names_the_version_tests_folder(self):
        """``version-tests/``, where TE5's tests live (design 5.3)."""
        self.assertIn("version-tests/", self.body)

    def test_release_routing_row_is_built(self):
        """The "release v0.1" row routes to the Version release and does not say "not built"."""
        rows = [row for row in routing_rows(self.body) if "release v0.1" in row[0]]
        self.assertEqual(len(rows), 1, routing_rows(self.body))
        text = " | ".join(rows[0])
        self.assertIn("Version release", text)
        self.assertNotIn("not built", text.lower())

    def test_rule_routing_row_is_built(self):
        """The "add a rule" row routes to the Rule change and does not say "not built" (F09)."""
        rows = [row for row in routing_rows(self.body) if "add a rule" in row[0]]
        self.assertEqual(len(rows), 1, routing_rows(self.body))
        text = " | ".join(rows[0])
        self.assertIn("Rule change", text)
        self.assertNotIn("not built", text.lower())


def routing_section(body: str) -> str:
    """The text of ``## Routing`` up to the next ``## `` heading, or "" when it is missing."""
    lines = body.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Routing"), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
               len(lines))
    return "\n".join(lines[start:end])


class VersionReachTests(unittest.TestCase):
    """D203 (F07 design 4 and 16), tstack issue #52: "Start v0.1" reaches the whole version.

    A feature-loop request that names a version reaches that version's remaining features; the
    reach ends before the release, which stays its own request.
    """

    @classmethod
    def setUpClass(cls):
        """Cuts the Routing section out of SKILL.md; empty when the file or section is missing."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        body = split_skill(text)[1]
        cls.section = routing_section(body)
        cls.rows = routing_rows(body)
        cls.bullets = [line for line in cls.section.split("\n") if line.startswith("- **How far")]

    def row_cell(self, flow: str) -> str:
        """The request cell of the routing row whose flow cell is exactly ``flow``."""
        cells = [row[0] for row in self.rows if len(row) == 2 and row[1] == flow]
        self.assertEqual(len(cells), 1, f"one {flow} row expected, got {cells}")
        return cells[0]

    def how_far(self) -> str:
        """The one ``- **How far`` bullet of the Routing section."""
        self.assertEqual(len(self.bullets), 1, self.bullets)
        return self.bullets[0]

    def test_feature_loop_row_lists_start_v01(self):
        """The Feature loop row's request cell lists "Start v0.1", with the double quotes."""
        self.assertIn('"Start v0.1"', self.row_cell("Feature loop"))

    def test_feature_loop_row_keeps_its_examples(self):
        """The Feature loop row still lists "next feature", "F04", "F04 to F06", and the rest."""
        cell = self.row_cell("Feature loop")
        for example in ('"next feature"', '"F04"', '"F04 to F06"', '"the rest of v0.1"'):
            with self.subTest(example=example):
                self.assertIn(example, cell)

    def test_start_v01_is_only_in_the_feature_loop_row(self):
        """No other routing row claims "Start v0.1"."""
        others = [row[0] for row in self.rows if len(row) == 2 and row[1] != "Feature loop"]
        self.assertTrue(others)
        for cell in others:
            self.assertNotIn('"Start v0.1"', cell)

    def test_version_release_row_keeps_release_v01(self):
        """The Version release row's request cell still lists "release v0.1"."""
        self.assertIn('"release v0.1"', self.row_cell("Version release"))

    def test_how_far_names_d203_and_d63(self):
        """The How far bullet names D203 and still D63."""
        bullet = self.how_far()
        self.assertRegex(bullet, r"\bD203\b")
        self.assertRegex(bullet, r"\bD63\b")

    def test_how_far_says_a_named_version_reaches_not_yet_accepted_features(self):
        """The How far bullet says a request naming a version reaches the features not yet
        accepted."""
        bullet = self.how_far()
        self.assertIn("not yet accepted", bullet)
        self.assertIn("version", bullet)

    def test_how_far_says_approvals_still_stop_the_loop(self):
        """The How far bullet says Troy's approvals still stop the loop and that it goes on
        after Troy approves."""
        bullet = self.how_far()
        self.assertRegex(bullet, r"(?i)approvals?\b.*\bstops?\b|\bstops?\b.*approvals?\b")
        self.assertRegex(bullet, r"(?i)\bafter Troy approves, (go|goes) on\b")

    def test_how_far_ends_the_reach_before_the_release(self):
        """The How far bullet says the reach ends before the release and names "release v0.1"
        as its own request."""
        bullet = self.how_far()
        self.assertRegex(bullet, r"(?i)\bends before\b[^.]*\brelease\b")
        self.assertRegex(bullet, r"(?i)own request|request of its own")
        self.assertIn('"release v0.1"', bullet)


def section(body: str, heading: str) -> str:
    """The text from a heading line up to the next heading of the same level or higher.

    Args:
        body: The skill's text after the front matter.
        heading: The whole heading line, such as ``### Merging``.

    Returns:
        The section, its heading included, or "" when the heading is missing.
    """
    level = len(heading) - len(heading.lstrip("#"))
    lines = body.split("\n")
    start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return ""
    fenced = False
    for end in range(start + 1, len(lines)):
        line = lines[end]
        if line.lstrip().startswith("```"):
            fenced = not fenced
        marks = len(line) - len(line.lstrip("#"))
        if not fenced and 0 < marks <= level and line[marks:marks + 1] == " ":
            return "\n".join(lines[start:end])
    return "\n".join(lines[start:])


def sentences(text: str) -> list:
    """The text's sentences, split after ``.``, ``!``, or ``?`` and at line breaks."""
    return [part for line in text.split("\n") for part in re.split(r"(?<=[.!?])\s+", line)
            if part.strip()]


class WaitChecksSkillTests(unittest.TestCase):
    """D204 (F07 design 3.1, 8.6, and 16), tstack issue #68: the merge waits with ``wait-checks``.

    In the pilot, ``gh pr checks --watch`` said that no checks were reported, and the merge
    chained after it with ``;`` ran anyway. The skill's merge step now waits with the engine's
    ``wait-checks`` and runs the merge as its own command after reading the wait's exit code.
    """

    @classmethod
    def setUpClass(cls):
        """Cuts the Merging and engine sections out of SKILL.md; empty when missing."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        cls.body = split_skill(text)[1]
        cls.merging = section(cls.body, "### Merging")
        cls.engine = section(cls.body, "## The engine")

    def test_merging_names_the_wait(self):
        """The Merging section names ``troy_flow.py wait-checks --pr <number> --sha <sha>``."""
        self.assertIn(WAIT_TEXT, self.merging)

    def test_merging_names_the_merge_with_the_pushed_head(self):
        """The Merging section names ``gh pr merge <number> --rebase --delete-branch
        --match-head-commit <sha>``."""
        self.assertIn(MERGE_TEXT, self.merging)

    def test_merging_no_longer_watches_gh_pr_checks(self):
        """The Merging section no longer names ``gh pr checks <number> --watch``."""
        self.assertNotEqual(self.merging, "")
        self.assertNotIn(OLD_WAIT_TEXT, self.merging)

    def test_merge_is_never_chained_with_a_semicolon(self):
        """A sentence of the Merging section says the merge never runs chained after the
        wait with ``;``: it names the merge, ``chain``, ``never``, and `` `;` ``."""
        found = [s for s in sentences(self.merging)
                 if "`;`" in s and re.search(r"(?i)\bchain", s) and re.search(r"(?i)\bnever\b", s)
                 and re.search(r"(?i)\bmerge", s)]
        self.assertTrue(found, self.merging)

    def test_no_command_chains_the_wait_and_the_merge(self):
        """No code span of the skill runs ``wait-checks`` and ``gh pr merge`` on one line."""
        self.assertNotEqual(self.body, "")
        spans = re.findall(r"`([^`\n]+)`", self.body)
        chained = [s for s in spans if "wait-checks" in s and "gh pr merge" in s]
        self.assertEqual(chained, [])

    def test_engine_table_has_a_wait_checks_row(self):
        """The table of "## The engine" has one row that starts ``| `troy_flow.py wait-checks``."""
        rows = [line for line in self.engine.split("\n")
                if line.startswith("| `troy_flow.py wait-checks")]
        self.assertEqual(len(rows), 1, self.engine)


def table_rows(text: str) -> list:
    """The rows of the Markdown tables in a text, as lists of trimmed cells, separators left out.
    """
    rows = []
    for line in text.split("\n"):
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                rows.append(cells)
    return rows


class SecurityReviewSkillTests(unittest.TestCase):
    """tstack #75 (F08 design 5.9, F04 D283): the release's security review in the skill.

    The release steps name the step ``security-review``, CR2's brief, ``release.review``'s
    commands, and the comment heading. The sections "Running a role" and "The summary for
    Troy" do not change, so they name none of it.
    """

    @classmethod
    def setUpClass(cls):
        """Cuts the Version release, release steps, and two unchanged sections out of SKILL.md."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        body = split_skill(text)[1]
        cls.release = section(body, "## Version release")
        cls.steps = section(body, "### The release steps")
        cls.unchanged = {name: section(body, f"## {name}")
                         for name in ("Running a role", "The summary for Troy")}

    def test_steps_table_has_the_review_before_the_release_test(self):
        """The release steps' table has a ``security-review`` row, before ``release-test``."""
        rows = table_rows(self.steps)
        review = [i for i, row in enumerate(rows) if "`security-review`" in row[0]]
        test = [i for i, row in enumerate(rows) if "`release-test`" in row[0]]
        self.assertEqual(len(review), 1, rows)
        self.assertEqual(len(test), 1, rows)
        self.assertLessEqual(review[0], test[0], rows)

    def test_names_cr2s_brief(self):
        """The release steps run CR2 with ``brief --task CR2``."""
        self.assertIn("brief --task CR2", self.release)

    def test_names_the_review_commands(self):
        """The release steps run the commands of ``release.review``."""
        found = [s for s in sentences(self.release)
                 if "release.review" in s and re.search(r"(?i)\bcommands?\b", s)]
        self.assertTrue(found, self.release)

    def test_names_the_comment_heading(self):
        """The release steps post the report as ``Security review, run <n>:``, the run number
        written as a placeholder such as ``<n>``."""
        self.assertRegex(self.release, r"Security review, run <[^<>\n]+>:")

    def test_running_a_role_and_the_summary_do_not_change(self):
        """Neither unchanged section names the security review's step, task, or heading."""
        for name, text in self.unchanged.items():
            with self.subTest(section=name):
                self.assertNotEqual(text, "", name)
                for word in ("security-review`", "CR2", "Security review", "release.review"):
                    self.assertNotIn(word, text)


class NotesSkillTests(unittest.TestCase):
    """tstack #67 (F07 design 6.6, D285; the build contract, section F): notes for later features.

    The skill gains ``## Notes for later features``, which names the engine's ``note`` command
    with its options, the check of the comment's file, and the post. Its section "One stage"
    points there. The sections "Running a role" and "The summary for Troy" do not change, so
    they say nothing of notes.
    """

    WORDS = ("troy_flow.py note", "--for", "--from", "--file", "check-text", "gh issue comment")

    @classmethod
    def setUpClass(cls):
        """Cuts the new section, One stage, and the two unchanged sections out of SKILL.md."""
        text = SKILL.read_bytes().decode("utf-8") if SKILL.is_file() else ""
        body = split_skill(text)[1]
        cls.notes = section(body, "## Notes for later features")
        cls.stage = section(body, "### One stage")
        cls.unchanged = {name: section(body, f"## {name}")
                         for name in ("Running a role", "The summary for Troy")}

    def test_has_the_section(self):
        """A level-2 heading ``## Notes for later features`` with text under it."""
        self.assertNotEqual(self.notes.strip(), "")
        self.assertGreater(len(self.notes.strip().split("\n")), 1, self.notes)

    def test_section_names_the_command_its_options_and_the_post(self):
        """``troy_flow.py note``, ``--for``, ``--from``, ``--file``, ``check-text``, and
        ``gh issue comment``, each in the section itself."""
        for word in self.WORDS:
            with self.subTest(word=word):
                self.assertIn(word, self.notes)

    def test_note_is_named_as_a_command(self):
        """``troy_flow.py note`` as a whole word, not as the start of another command."""
        self.assertRegex(self.notes, r"troy_flow\.py note(?![\w-])")

    def test_one_stage_points_to_it(self):
        """The section "One stage" names section "Notes for later features"."""
        self.assertNotEqual(self.stage, "")
        self.assertIn('"Notes for later features"', self.stage)

    def test_running_a_role_and_the_summary_do_not_change(self):
        """Neither unchanged section names a note, the command, or its post."""
        for name, text in self.unchanged.items():
            with self.subTest(section=name):
                self.assertNotEqual(text, "", name)
                for word in ("troy_flow.py note", "Note for", "Notes for later features",
                             "--for", "gh issue comment"):
                    self.assertNotIn(word, text)
                self.assertNotRegex(text, r"(?i)\bnotes?\b")


if __name__ == "__main__":
    unittest.main()
