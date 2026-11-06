"""Tests for test tags (design 4.1): how a test's own name is read."""

import unittest

from code_helpers import run_code
from helpers import parallel
from prefetch import PrefetchedCase
from reports import Case, junit

TITLE = "[docs] Notes"

TAGGED = {
    "python test prefix": "test_f04_t07_writes_header",
    "upper case": "test_F04_T07_writes_header",
    "dashes": "test_f04-t07-writes-header",
    "mixed dash and underscore": "test_F04-t07_writes_header",
    "no test prefix": "F04_T07_WritesHeader",
    "three digit feature": "test_f123_t07_x",
    "case id alone": "test_f04_t07",
    "parameter suffix": "test_f04_t07_writes[param-1]",
    "parameter suffix with dot": "test_f04_t07_writes[a.b]",
    "bug id": "test_b12_empty_history_does_not_crash",
    "bug id upper case": "B12_EmptyHistory",
    "big bug number": "test_b1234_x",
    "small bug number": "test_b7_x",
    "suite dot test": "ExportCsv.F04_T07_WritesHeader",
    "suite dot python name": "Suite.test_f04_t07_x",
    "dot inside parameter": "test_f04_t07[x.y.z]",
}
UNTAGGED = {
    "no id": "test_writes_header",
    "one digit feature": "test_f4_t07_x",
    "one digit case": "test_f04_t7_x",
    "four digit feature": "test_f1234_t07_x",
    "id not at the start": "test_writes_f04_t07",
    "id only in the parameter": "test_writes[f04_t07]",
    "id only in the suite": "F04_T07.WritesHeader",
    "bug without number": "test_b_x",
    "feature without case": "test_f04_x",
    "empty after prefix": "test_",
}


class TagTests(PrefetchedCase):
    """Passing tests are judged by their names alone (kind ``docs``, no history)."""

    def r10(self, name: str) -> str:
        """Returns R10's result for one passing test with the given name."""
        return run_code(TITLE, junit=[junit([Case(name)])]).status("R10")

    def check_all(self, names: dict, expected: str) -> None:
        """Asserts R10's result for every name in a mapping."""
        results = parallel(self.r10, list(names.values()))
        for label, result in zip(names, results):
            with self.subTest(case=label, name=names[label]):
                self.assertEqual(result, expected)

    def test_tagged_names_pass(self):
        """Names that start with a case ID or a bug ID are accepted."""
        self.check_all(TAGGED, "pass")

    def test_untagged_names_fail(self):
        """Names without a leading ID fail R10 even when the test passes."""
        self.check_all(UNTAGGED, "fail")

    def test_one_untagged_test_fails_the_whole_run(self):
        """A single untagged test among tagged ones fails R10."""
        cases = [Case("test_f04_t01_a"), Case("test_f04_t02_b"), Case("test_plain")]
        out = run_code(TITLE, junit=[junit(cases)])
        self.assert_rule(out, "R10", "fail")
        self.assert_exit(out, 1)

    def test_all_tagged_tests_of_several_features_pass(self):
        """Tests of different features and bugs are all fine when they pass."""
        cases = [Case("test_f04_t01_a"), Case("test_f05_t01_b"), Case("test_b12_c")]
        out = run_code(TITLE, junit=[junit(cases)])
        self.assert_rule(out, "R10", "pass")
        self.assert_clean(out)


if __name__ == "__main__":
    unittest.main()
