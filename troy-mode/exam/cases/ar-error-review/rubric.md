# What a good output does

Each output is the Architect's review of one interface design, the change in `change.patch`
(the design of `recipe-menu menu new` and `menu show`), and the review's entries in the design's
section 4. The architecture is in `shared/docs/architecture.md`; its section 6 holds the error
handling rules.

Key:
- K1: When `menu new` cannot list the `menus` folder, the failure's first line names that folder
  by its full path. Architecture 6 allows a full path for `menu new` only for a file it could not
  write (ADR-0009 keeps that scope on purpose), so this is an architecture change that Troy
  approves: the design must put it to Troy, for example as a new point with options.

1. A finding states K1: the full path for a failed listing of `menus` goes beyond architecture 6,
   and the design must put it to Troy or name the folder as architecture 6 does. Quote it.
2. No finding is false: each one's claim about the design or the architecture is true. Fail, and
   name it, when a finding says the design has or lacks something that it does not.
3. The review's entries in section 4 of the design give a result for each checklist row and a
   row in the rounds log. Fail when section 4 still says "Not reviewed yet." or lacks the rounds
   log row.
