Role: Code Reviewer
Task: CR1, F04, [F04 4/6 tests] Recipe files
Result: approved
Changed files: None
Checks: the brief's checks pass
Summary: The 58 tests follow the approved plan, and every expected value agrees with the design, the example data, and a scratch model of design 1.0, against which 269 tests pass and 2 are skipped; the order cases and the line numbers of F04-T34 included. Each test fails against the mock for the intended reason, and no other test passes against it. ruff and mypy pass, the security review found nothing, and all 26 message texts and 9 places of `f04_support.py` equal the design's. The Linux paths of F04-T12, T36, T51, T52, and T53 fit the plan, read but not run.
Findings: None
Question: None
