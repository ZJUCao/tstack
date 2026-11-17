# What a good output does

Each output is the Test Manager's review of the tests in `change.patch` against the test plan in
`shared/docs/features/F13-shopping-list-command/test-plan.md`. The key holds the tests that check
less than their plan case expects, which a good review finds.

Key:
- K1: F13-T05 input 10 adds an entry `2026-W47.md` that the plan's folder does not hold, and
  checks only the modification times of the other entries where the plan expects their bytes.
- K2: F13-T09 input 11 checks only that the path is a folder, where the plan says it stays an
  empty folder.
- K3: F13-T18 input 1 checks only the exit code of `menu show 2026-W99`, where the plan expects
  the error line too.
- K4: F13-T29 builds 40 folders where the plan says 100.

1. The findings state at least two of K1, K2, and K3. Quote them.
2. A finding states K4. Quote it.
3. No finding is false: each one's claim about a test or the plan is true. Fail, and name it.
