# What a good output does

Each output is the Architect's review of one interface design, the change in `change.patch`
(the design of `recipe-menu init`). A review gives a Result and numbered findings. The key holds
the problems that a good review of this design finds.

Key:
- K1: Choice 9's account of folder values that end with a space or a dot on Windows is wrong:
  when the folder exists, its listing does not fail, and Windows drops one trailing dot from a
  path part, so a value ending in a single dot works.
- K2: Choice 8 and the failure lines of 2.2 name the problem's file by its full path, while
  architecture 6 says that a problem names its file relative to the data folder; the design must
  name the rule it departs from and why, and put it to Troy.
- K4: Several lines of the python examples are wider than 100 columns, which `ruff format`
  with the project's settings rewraps.

1. A finding states K1 or a close equivalent: that the design's account of a trailing space or
   dot on Windows is wrong in at least one of the two ways. Quote it.
2. A finding states K2: the full path in a failure departs from architecture 6, and the design
   must say so or put it to Troy. Quote it.
3. A finding states K4: python example lines over 100 columns, or examples that `ruff format`
   would change. Quote it.
4. No finding is false: each one's claim about the design is true of `change.patch`. Fail, and
   name it, when a finding says the design has or lacks something that it does not.
