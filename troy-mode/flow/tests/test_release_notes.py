"""release-notes (F08 design 3.1, 5.7, 11.1; interface note section 10).

The tag's section of ``CHANGELOG.md`` on origin/main, written to a file for
the GitHub release's notes.

Planted bug of F08 design 11.2 caught here: "notes taken from the wrong
section": ``ReleaseNotesTests.test_middle_section_stops_before_the_next``,
``test_tag_must_end_at_a_space_or_parenthesis``, and
``test_last_section_stops_at_a_level_one_heading``.
"""

import unittest

from flow_helpers import (
    CHANGELOG, Fakes, FlowCase, Project, SCRATCH, base_files, base_step, crlf, front_matter,
    new_dir, parallel, run_engine,
)

TEXT = (front_matter("changelog", "en", "1.3", "CHANGELOG.zh-CN.md", "Up to date with v0.3.0.",
                     "2026-12-01")
        + "# Changelog\n\n"
        "## v0.3.0\n\n### Fixed\n\n- B30: Wrong total for two files.\n\n"
        "## v0.2.0 (2026-12-01)\n\n### Added\n\n- F03: Counts characters.\n\n"
        "## v0.1.10 (2026-11-30)\n\n### Fixed\n\n- B20: Wrong total.\n\n"
        "## v0.1.1 (2026-11-20)\n\n### Fixed\n\n- B14: Crash on an empty file.\n\n"
        "```text\n## v0.1.0 inside a fence is not a heading\n```\n\n\n"
        "## v0.1.0 (2026-11-09)\n\n### Added\n\n- F01: Counts words.\n- F02: Counts lines.\n\n"
        "# Appendix\n\nNot part of any section.\n")
EXPECTED = {
    "v0.3.0": "## v0.3.0\n\n### Fixed\n\n- B30: Wrong total for two files.\n",
    "v0.2.0": "## v0.2.0 (2026-12-01)\n\n### Added\n\n- F03: Counts characters.\n",
    "v0.1.10": "## v0.1.10 (2026-11-30)\n\n### Fixed\n\n- B20: Wrong total.\n",
    "v0.1.1": ("## v0.1.1 (2026-11-20)\n\n### Fixed\n\n- B14: Crash on an empty file.\n\n"
               "```text\n## v0.1.0 inside a fence is not a heading\n```\n"),
    "v0.1.0": "## v0.1.0 (2026-11-09)\n\n### Added\n\n- F01: Counts words.\n- F02: Counts lines.\n",
}


class ReleaseNotesTests(FlowCase):
    """The section of one tag, exactly (note section 10)."""

    @classmethod
    def setUpClass(cls):
        """A clone whose origin/main holds the changelog and whose branch changes it."""
        cls.project = Project([base_step(base_files(extra={CHANGELOG: TEXT}))])
        cls.project.commit("[docs] Reword v0.1.1", {CHANGELOG: TEXT.replace(
            "- B14: Crash on an empty file.", "- B14: Reworded on the branch.")})
        cls.project.write(CHANGELOG, TEXT.replace("- F01: Counts words.", "- F01: In the tree."))
        cls.fakes = Fakes(fail=True)
        cls.folder = new_dir("notes")

        def run(tag):
            """Writes one tag's notes to its own file."""
            out = str(cls.folder / f"notes-{tag}.md")
            return cls.project.run("release-notes", "--tag", tag, "--out", out,
                                   fakes=cls.fakes), out
        tags = list(EXPECTED)
        cls.outs = dict(zip(tags, parallel(run, tags)))

    def notes(self, tag: str) -> bytes:
        """Asserts the run and returns the bytes written for the tag."""
        out, path = self.outs[tag]
        report = self.report_of(out, 0, "release-notes")
        self.assertEqual((report["tag"], report["source"], report["out"]),
                         (tag, "CHANGELOG.md", path))
        with open(path, "rb") as handle:
            return handle.read()

    def test_middle_section_stops_before_the_next(self):
        """v0.2.0's section ends before ``## v0.1.10``, with one final newline."""
        self.assertEqual(self.notes("v0.2.0"), EXPECTED["v0.2.0"].encode("utf-8"))

    def test_first_section_without_a_date(self):
        """``## v0.3.0`` with nothing after the tag is v0.3.0's section."""
        self.assertEqual(self.notes("v0.3.0"), EXPECTED["v0.3.0"].encode("utf-8"))

    def test_tag_must_end_at_a_space_or_parenthesis(self):
        """``## v0.1.10`` is not v0.1.1's section, and v0.1.10 has its own."""
        self.assertEqual(self.notes("v0.1.1"), EXPECTED["v0.1.1"].encode("utf-8"))
        self.assertEqual(self.notes("v0.1.10"), EXPECTED["v0.1.10"].encode("utf-8"))

    def test_fenced_heading_is_text_and_trailing_blank_lines_go(self):
        """The fenced ``## v0.1.0`` line stays in v0.1.1's section; blank lines after it go."""
        notes = self.notes("v0.1.1").decode("utf-8")
        self.assertIn("## v0.1.0 inside a fence is not a heading\n```\n", notes)
        self.assertTrue(notes.endswith("```\n") and not notes.endswith("\n\n"), notes)

    def test_last_section_stops_at_a_level_one_heading(self):
        """v0.1.0's section ends before ``# Appendix``."""
        self.assertEqual(self.notes("v0.1.0"), EXPECTED["v0.1.0"].encode("utf-8"))

    def test_read_from_origin_main(self):
        """The branch's and the tree's edits do not reach the notes."""
        self.assertNotIn(b"Reworded on the branch", self.notes("v0.1.1"))
        self.assertNotIn(b"In the tree", self.notes("v0.1.0"))

    def test_never_calls_gh(self):
        """A gh that fails on every call is never called."""
        self.notes("v0.2.0")
        self.assertEqual(self.fakes.gh_calls(), [])


class CrlfAndRefusalTests(FlowCase):
    """A CRLF changelog, a missing one, a missing section, and bad input (note section 10)."""

    def test_crlf_changelog_gives_lf_notes(self):
        """A CRLF ``CHANGELOG.md`` on origin/main: the notes have LF endings."""
        project = Project([base_step(base_files(extra={CHANGELOG: crlf(TEXT)}))])
        path = str(project.tmp / "notes.md")
        self.report_of(project.run("release-notes", "--tag", "v0.2.0", "--out", path))
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), EXPECTED["v0.2.0"].encode("utf-8"))

    def test_refusals(self):
        """No changelog on origin/main or no section: exit 1. A bad tag, no repository: exit 2."""
        with_log = Project([base_step(base_files(extra={CHANGELOG: TEXT}))])
        without = Project([base_step()])
        without.write(CHANGELOG, TEXT)
        cases = {
            "no changelog on origin/main": (without, "v0.1.0", 1),
            "no section": (with_log, "v0.4.0", 1),
            "tag without the patch": (with_log, "v0.1", 2),
            "tag without v": (with_log, "0.1.0", 2),
            "control": (with_log, "v0.1.0", 0),
        }

        def run(name):
            """Runs release-notes for one case."""
            project, tag, _ = cases[name]
            return project.run("release-notes", "--tag", tag, "--out",
                               str(project.tmp / f"{name.replace(' ', '-')}.md"))
        names = list(cases)
        for name, out in zip(names, parallel(run, names)):
            with self.subTest(case=name):
                code = cases[name][2]
                if code == 0:
                    self.report_of(out, 0, "release-notes")
                elif code == 1:
                    self.assertNotEqual(self.report_of(out, 1, "release-notes")["problems"], [])
                else:
                    self.assert_exit(out, 2)
        plain = new_dir("plain")
        out = run_engine(["release-notes", "--tag", "v0.1.0", "--out", str(plain / "n.md"),
                          "--repo", plain, "--json"], SCRATCH, Fakes(fail=True))
        self.assert_exit(out, 2)


if __name__ == "__main__":
    unittest.main()
