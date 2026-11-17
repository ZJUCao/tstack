# What a good output does

Each output is the interface design of `recipe-menu init`, which creates a data folder, and of
the `datafile` function that writes its files. The architecture, in `shared/docs/architecture.md`
(section 6 holds the error handling rules), says how errors are reported. The key lists what the
pilot's design got wrong and its reviewer caught.

Key:
- K1: On Windows, a data folder value that ends with spaces or dots. Windows drops one trailing
  dot from a path part, so `--data "...\recipe-menu."` works, and an existing folder whose value
  ends with a space can still be listed. A design that says such a value always fails, or says
  that the listing of an existing folder fails, is wrong.
- K2: A failure's first line that names a file by its full path, while architecture 6 says that a
  problem names its file relative to the data folder. The design must name the rule it departs
  from, say why, and put the departure to Troy as an open question.
- K3: A Ctrl+C or a failed removal in the middle of creating the files: what is left, and the
  exit code.

1. The design's account of folder values that end with spaces or dots on Windows is right (K1),
   or the design leaves such values out of scope and says so. Fail, and quote it, when it states a
   wrong behavior.
2. Every failure or refusal line follows architecture 6's rules for naming files, or the design
   names the rule it departs from, says why, and lists the departure for Troy (K2). Fail, and
   quote the line, when a failure names its file by its full path with none of that.
3. The design says what an interruption (Ctrl+C) or a failed removal leaves behind and which exit
   code follows (K3). Fail when it says nothing about them.
