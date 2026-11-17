# What a good output does

Each output is the Code Reviewer's review of a mock, the change in `change.patch`: interfaces in
Python whose bodies only raise `NotImplementedError`, with doc comments. The key holds the
problems of the mock's doc comments that a good review finds.

Key:
- K1: The class doc comment of `Arguments` (src/recipe_menu/app/_arguments.py) says that it sorts
  the pairs by name, but the mock does not sort, and nothing says that the mock leaves the sort
  out.
- K2: In `UsageError` (src/recipe_menu/app/_usage_error.py), the note "The mock leaves these
  checks out." ends a paragraph that describes the design's checks instead of standing alone; or
  `__init__`'s Raises section lists only `NotImplementedError`, without the errors of the design.

1. A finding states K1. Quote it.
2. A finding states K2, either part. Quote it.
3. No finding is false: each one's claim about the change is true of `change.patch`. Fail, and
   name it.
