"""Tests for R16: changed dependency files are flagged (design section 6.5)."""

import unittest

from helpers import CheckTestCase, make_config, run_pr

CONFIG = make_config(
    paths={"dependencies": ["pyproject.toml", "requirements*.txt", "**/package.json"]}
)
IMPL = "[F04 5/6 impl] Change"


class R16Tests(CheckTestCase):
    """Dependency changes warn and never fail."""

    def test_manifest_changed_warns_and_lists_it(self):
        """A changed manifest gives a warning that names the file."""
        out = run_pr(IMPL, {"pyproject.toml": "[project]\n", "src/a.py": "x\n"}, config=CONFIG)
        self.assert_rule(out, "R16", "warn")
        self.assert_paths(out, "R16", ["pyproject.toml"])
        self.assert_clean(out)

    def test_no_manifest_passes(self):
        """A PR with no dependency file passes R16."""
        out = run_pr(IMPL, {"src/a.py": "x\n"}, config=CONFIG)
        self.assert_rule(out, "R16", "pass")

    def test_every_changed_dependency_file_is_listed(self):
        """Each matching path gets its own detail, nested ones included."""
        changes = {
            "pyproject.toml": "a\n",
            "requirements-dev.txt": "b\n",
            "web/app/package.json": "{}\n",
            "src/a.py": "x\n",
        }
        out = run_pr(IMPL, changes, config=CONFIG)
        self.assert_rule(out, "R16", "warn")
        self.assert_paths(
            out, "R16", ["pyproject.toml", "requirements-dev.txt", "web/app/package.json"]
        )

    def test_deleted_manifest_warns(self):
        """Deleting a dependency file counts as a change."""
        out = run_pr(IMPL, {"pyproject.toml": None, "src/a.py": "x\n"}, config=CONFIG,
                     base_files={"pyproject.toml": "[project]\n"})
        self.assert_rule(out, "R16", "warn")

    def test_renamed_manifest_warns(self):
        """Renaming a dependency file counts as a change."""
        out = run_pr("[F04 5/6 impl] Rename", config=CONFIG,
                     base_files={"requirements.txt": "pytest\nrequests\nrich\n"},
                     renames=[("requirements.txt", "requirements-dev.txt")])
        self.assert_rule(out, "R16", "warn")

    def test_never_fails_even_when_r02_does(self):
        """A dependency change in a docs PR fails R02 but only warns in R16."""
        out = run_pr("[docs] Notes", {"pyproject.toml": "[project]\n"}, config=CONFIG)
        self.assert_rule(out, "R16", "warn")
        self.assert_rule(out, "R02", "fail")

    def test_warning_alone_keeps_exit_code_zero(self):
        """A warning does not block the PR."""
        out = run_pr("[rules] Pin", {"pyproject.toml": "[project]\n"}, config=CONFIG)
        self.assert_rule(out, "R16", "warn")
        self.assert_exit(out, 0)
        self.assertTrue(out.report["ok"])

    def test_without_configuration_no_file_is_a_dependency(self):
        """With no dependencies patterns, nothing is flagged."""
        out = run_pr(IMPL, {"pyproject.toml": "[project]\n"})
        self.assert_rule(out, "R16", "pass")


if __name__ == "__main__":
    unittest.main()
