# What a good output does

Each output is the interface design of a feature, with Python examples in fenced code blocks.
The check by script decides this case: `ruff format --check`, with the project's settings,
accepts every python block. These criteria say the same for a reader.

1. No line of a python block is longer than the project's line length, 100 columns.
2. Every python block uses the quote style that `ruff format` gives: double quotes, except where a
   string holds a double quote and no single quote.
3. Every python block is laid out as `ruff format` lays it out: its wrapping, blank lines, and
   trailing commas.
