"""Tests for R02: one stage per PR, and path classes (design sections 5, 6.2)."""

import unittest

from helpers import CheckTestCase, lines, make_config, parallel, pr_sandbox, run_pr

# Every changed path mapped to the class the design gives it.
CONFIG = make_config(
    paths={
        "docs": ["notes/*.txt", "d?.txt"],
        "dependencies": ["requirements.txt", "tests/pins.txt"],
        "tests": ["**/test_*.py"],
        "config": ["ci/**"],
    }
)
CLASSES = {
    ".troy-mode/a/b.txt": "config",
    ".github/workflows/x.yml": "config",
    "docs/rules.md": "config",
    "docs/rules.zh-CN.md": "config",
    ".gitignore": "config",
    ".gitattributes": "config",
    ".editorconfig": "config",
    "ci/run.sh": "config",
    "requirements.txt": "dependencies",
    "tests/pins.txt": "dependencies",
    "tests/test_a.py": "tests",
    "test/data.md": "tests",
    "tests/readme.md": "tests",
    "src/test_util.py": "tests",
    "docs/guide.md": "docs",
    "docs/a/b/c.txt": "docs",
    "README.md": "docs",
    "sub/dir/notes.md": "docs",
    "LICENSE": "docs",
    "LICENSE-MIT": "docs",
    "notes/a.txt": "docs",
    "d1.txt": "docs",
    "src/app.py": "source",
    "src/docs/a.txt": "source",
    "sub/LICENSE": "source",
    "notes/sub/a.txt": "source",
    "d12.txt": "source",
}
KINDS = {
    "[F04 1/6 design] x": {"docs"},
    "[F04 2/6 test-plan] x": {"docs"},
    "[F04 6/6 accept] x": {"docs"},
    "[docs] x": {"docs"},
    "[F04 3/6 mock] x": {"source", "dependencies"},
    "[F04 5/6 impl] x": {"source", "dependencies"},
    "[B12 B/B fix] x": {"source", "dependencies"},
    "[refactor] x": {"source", "dependencies"},
    "[F04 4/6 tests] x": {"tests", "dependencies"},
    "[B12 A/B test] x": {"tests", "dependencies"},
    "[F04 test-fix] x": {"tests", "dependencies"},
    "[rules] x": {"config", "dependencies"},
}


class PathClassTests(CheckTestCase):
    """Checks every kind against one PR that touches every class."""

    @classmethod
    def setUpClass(cls):
        """Builds one PR that adds a file of each class."""
        cls.sb = pr_sandbox({path: "x\n" for path in CLASSES}, config=CONFIG)
        cls.addClassCleanup(cls.sb.close)

    def test_each_kind_may_change_only_its_allowed_classes(self):
        """R02 fails exactly for the paths whose class the kind may not change."""
        outs = parallel(self.sb.check_pr, list(KINDS))
        for (title, allowed), out in zip(KINDS.items(), outs):
            with self.subTest(title=title):
                expected = [p for p, c in CLASSES.items() if c not in allowed]
                self.assert_rule(out, "R02", "fail")
                self.assertEqual(sorted(out.paths("R02")), sorted(expected), out.describe())
                self.assert_exit(out, 1)


class R02Tests(CheckTestCase):
    """Covers the named R02 cases from the design."""

    def test_source_file_in_docs_pr_fails_with_its_path(self):
        """A source file in a docs PR fails and names the path."""
        out = run_pr("[docs] Notes", {"docs/a.md": "a\n", "src/app.py": "x = 1\n"})
        self.assert_rule(out, "R02", "fail")
        self.assert_paths(out, "R02", ["src/app.py"])

    def test_docs_only_pr_passes(self):
        """A docs PR that changes only documents passes."""
        out = run_pr("[docs] Notes", {"docs/a.md": "a\n", "README.md": "r\n"})
        self.assert_rule(out, "R02", "pass")
        self.assert_clean(out)

    def test_dependency_file_in_tests_pr_passes(self):
        """A configured dependency file may change in a tests PR."""
        config = make_config(paths={"dependencies": ["pyproject.toml"]})
        out = run_pr(
            "[F04 4/6 tests] Tests",
            {"tests/test_a.py": "x\n", "pyproject.toml": "[project]\n"},
            config=config,
        )
        self.assert_rule(out, "R02", "pass")

    def test_dependency_file_in_docs_pr_fails(self):
        """A configured dependency file may not change in a docs PR."""
        config = make_config(paths={"dependencies": ["pyproject.toml"]})
        out = run_pr("[docs] Notes", {"pyproject.toml": "[project]\n"}, config=config)
        self.assert_rule(out, "R02", "fail")
        self.assert_paths(out, "R02", ["pyproject.toml"])

    def test_manifest_is_source_without_configuration(self):
        """With no dependencies pattern, pyproject.toml is a source file."""
        out = run_pr("[F04 4/6 tests] Tests", {"pyproject.toml": "[project]\n"})
        self.assert_rule(out, "R02", "fail")
        self.assert_paths(out, "R02", ["pyproject.toml"])

    def test_rename_from_source_to_docs_fails_on_old_path(self):
        """Moving a source file into docs in a docs PR fails on the old path."""
        out = run_pr(
            "[docs] Move", base_files={"src/a.py": lines(5, "code")},
            renames=[("src/a.py", "docs/a.md")],
        )
        self.assert_rule(out, "R02", "fail")
        self.assert_paths(out, "R02", ["src/a.py"])

    def test_rename_from_docs_to_source_fails_on_new_path(self):
        """Moving a document into source in a docs PR fails on the new path."""
        out = run_pr(
            "[docs] Move", base_files={"docs/b.md": lines(5, "text")},
            renames=[("docs/b.md", "src/b.py")],
        )
        self.assert_rule(out, "R02", "fail")
        self.assert_paths(out, "R02", ["src/b.py"])

    def test_rename_out_of_docs_in_source_pr_fails_on_old_path(self):
        """The old path of a rename is checked as well as the new one."""
        out = run_pr(
            "[F04 5/6 impl] Move", base_files={"docs/b.md": lines(5, "text")},
            renames=[("docs/b.md", "src/b.py")],
        )
        self.assert_rule(out, "R02", "fail")
        self.assert_paths(out, "R02", ["docs/b.md"])

    def test_rename_inside_one_class_passes(self):
        """A source-to-source rename passes in a refactor PR."""
        out = run_pr(
            "[refactor] Rename", base_files={"src/a.py": lines(5, "code")},
            renames=[("src/a.py", "src/b.py")],
        )
        self.assert_rule(out, "R02", "pass")

    def test_unknown_title_fails_r02(self):
        """A title that matches no pattern fails R02."""
        out = run_pr("Just some change", {"docs/a.md": "a\n"})
        self.assert_rule(out, "R02", "fail")
        self.assertIsNone(out.report["title"])

    def test_deleted_file_is_classified_by_its_path(self):
        """A deleted source file in a docs PR fails."""
        out = run_pr("[docs] Delete", {"src/a.py": None}, base_files={"src/a.py": "x\n"})
        self.assert_rule(out, "R02", "fail")
        self.assert_paths(out, "R02", ["src/a.py"])


if __name__ == "__main__":
    unittest.main()
