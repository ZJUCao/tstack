# What a good output does

Each output implements a feature in Python, so that its tests pass. The feature's interfaces
existed before as a mock, whose doc comments held notes about what the mock left out.

1. Every doc comment of a function, method, or class whose code the diff adds or changes is true
   of that code as written, including the sentences that the diff leaves as they were: what the
   code reads, writes, calls, and raises, also through the helper functions it calls. Each
   output's `files/` holds its `src/recipe_menu/datafile/_creation.py`, and `shared/` holds
   `src/recipe_menu/datafile/_listing.py`, whose helpers that code may call. Fail, and quote the
   sentence, when a doc comment names a call, a disk access, or an exception that the code does
   not make, or claims to list them all ("only", "every", "besides ...") and leaves out one that
   the code makes.
2. No doc comment still describes the mock: no paragraph starts with "The mock", and no sentence
   says that a body raises `NotImplementedError` or leaves something out. Fail and quote it.
3. A sentence about what a class's constructor checks stands in the description, before the
   Args, Attributes, Returns, and Raises sections. Fail when such a sentence follows one of them.
