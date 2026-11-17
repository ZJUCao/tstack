# What a good output does

Each output is the Code Reviewer's review of the tests in `change.patch` against the test plan in
`shared/docs/features/F04-recipe-files/test-plan.md`.

Key:
- K1: F04-T07 in tests/test_f04_recipe_ids.py writes the literal `"a\b"` in a normal Python
  string, which is `a`, BACKSPACE (U+0008), so the backslash separator of the plan is never
  tested.

1. A finding states K1: that `"a\b"` is a backspace, not a backslash, so the backslash case is
   not tested. Quote it.
2. No finding is false: each one's claim about a test or the plan is true. Fail, and name it.
3. Each blocking finding names its plan case or rule, the file and line, and the change asked for.
