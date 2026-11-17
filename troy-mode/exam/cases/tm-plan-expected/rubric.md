# What a good output does

Each output is the test plan of `recipe-menu menu new` and `menu show`. The design is in
`shared/docs/features/F11-create-and-show-a-week-menu/design.md`. A plan's expected results must
agree with the design and with what the case's own steps do. The key holds the contradictions
that the pilot's plan had, found only at the test review.

Key:
- K1: A case runs `menu new` for two weeks in one folder and then `check` there, but expects
  `check`'s count line to count one week menu ("1 week menu"), where the folder then holds two
  ("2 week menus").
- K2: A general statement of the plan, for example in its R09 paragraph ("every case that
  expects exit code 0 from `menu new` checks its three lines and the new file's bytes"), that some
  case rows do not keep.

1. Every expected count of week menus, meals, or dishes agrees with what the case's steps leave in
   the folder, as K1 does not. Fail, and quote the case and its expected result, for any count
   that the steps contradict.
2. Every general statement of the plan about what its cases check holds for every case row it
   covers (K2). Fail, and quote the statement and a row that breaks it.
3. Every expected output text agrees with the design's texts in the same language. Fail, and quote
   it, for a text that differs from the design.
