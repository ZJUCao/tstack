# What a good output does

Each output writes the tests of a feature's test plan. The checks by script decide this case:
the tests fail against the mock, pass on the real code, and catch changes to the real code that
break what the plan expects. These criteria say the same for a reader.

1. Each test checks every part of its plan case's expected result that the case names: the exit
   code, the output and error lines, and the bytes, presence, or emptiness of the files and
   folders. Fail when a test checks only the exit code, only that a path exists or is a folder,
   or only modification times where the case expects bytes.
2. Each test uses its plan case's inputs: no added file, entry, or argument, and the counts the
   case gives. Fail when a test changes an input or a count.
3. Every case of the plan has exactly one test whose name starts with the case's ID, and no test
   lies outside the plan.
