# What a good output does

Each output rewrites the module doc comments of five test support modules to follow the project
rule P01: a support module's doc comment states its purpose and its limits, and lists no names.
The judge sees the diff and the five files after the change.

Key, the false statements that a good output avoids in these files:
- K1: tests/f11_texts.py: "Every text is written out as a literal", although the output of an
  empty menu takes its dates and day labels from F06 and its layout from F02.
- K2: tests/f11_support.py: leaving out that the module builds the bytes of a new menu file and
  the meals of a new menu's lines, and holds the meal sets of the cases, while saying that "The
  expected texts are in f11_texts".
- K3: tests/f12_support.py: a limit on what the module holds at import that leaves out `None`,
  the unit of most rows of INGREDIENTS, or claims numbers it does not hold.
- K4: tests/f12_support.py: "the doc comment of each function says how it reads it" where the
  doc comments of `line` and `every_slot` do not say so.

1. Every statement in the five module doc comments, and in any function doc comment the diff
   changes, is true of the code in the file. Fail, and quote it, for any false statement, K1 to
   K4 included.
2. Each of the five module doc comments states the module's purposes, and its limits, such as
   what it does at import and what it does not import or call. Fail when a doc comment leaves out
   a purpose that the code plainly serves (K2) or has no limit.
3. No module doc comment lists the names that the module holds or imports. Fail and quote it.
