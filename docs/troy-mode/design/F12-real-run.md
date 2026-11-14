# F12 design: real-run acceptance

| | |
| --- | --- |
| Feature | F12 in [requirements 1.35](../requirements.md#72-feature-list) |
| Version | 1.0 |
| Date | 2026-11-14 |
| Status | Approved by Troy on 2026-11-14, with D101 to D114. |
| Source of truth | This English file. [`F12-real-run.zh-CN.md`](F12-real-run.zh-CN.md) is the Chinese mirror. |

## 1. Scope

Before a feature's acceptance PR (PR 6), the Product Manager runs the real program the way Troy would, through every command of the feature's prototype, and puts the real output and its comparison with the prototype in the PR (requirements 5.2). A mismatch goes to the bug flow (5.3) before acceptance. F12 builds this for command-line projects, whose prototypes are Markdown terminal transcripts (Q9). Projects with a graphical or web interface come later (Q13).

F12 delivers:

1. a run file next to each prototype, which says how the real run sets up each section of it (section 4, D103);
2. an engine command, `troy_flow.py real-run`, that replays the transcripts on the real program, compares the output, and writes the evidence (section 5, D102);
3. the real-run step in PR 6, run by the main session as the Product Manager (section 3, D101), with a new Test Manager task, TM8, that rules on each mismatch (section 7, D107);
4. the project status label "Ran for real on Troy's PC" (section 9, D109, Q12);
5. a real run of every accepted feature at each release test (section 11, D112);
6. a new plugin version that brings F12 into the pilot before its v0.1 release (section 13, D113, Q11).

F12 lands in one PR, as Q10 says for every feature.

## 2. Location

```text
troy-mode/
  flow/
    troyflow/
      realrun.py        the command: picks the prototypes, sets up, runs, reports (section 5)
      transcript.py     reads a prototype's transcripts (section 5.3)
      runfile.py        reads and checks a run file (section 4)
      realcompare.py    compares and renders the evidence (sections 5.6 and 8)
      cli.py            gains real-run
      brief.py          gains TM8
      releasetest.py    gains --real-run (section 11)
    tests/
      test_real_run*.py
  roles/
    product-manager.md  PM3 (section 12)
  templates/
    README.md           the new label, and its mirror (section 9)
    requirements.md     the Status comment, and its mirror
agents/
  troy-test-manager.md  TM8 (section 7)
skills/
  troy-mode/SKILL.md    the real run, TM8, and the release test (section 12)
docs/troy-mode/guide/   pages 03, 05, 07, and 08, and their mirrors (section 12)
.claude-plugin/
  plugin.json           the version (section 13)
```

The module names are a suggestion. In a project, the only new files are the run files:

```text
docs/prototypes/
  F09-list-show.md         the prototype, unchanged
  F09-list-show.run.toml   its run file, written by the Product Manager (section 4)
```

## 3. The real run in PR 6

PR 6 is the Product Manager's (PM3), in the main session. Only the main session talks with Troy, and F05's hooks put no limit on its commands apart from the git and gh guards of F05 section 8.2. The real run writes nothing in the repository, so no hook and no write scope changes (D101).

1. **Branch.** `troy-mode/<id>-6-accept` from `origin/main`, as now.
2. **Run files.** Under `snapshot --role product-manager`, the Product Manager writes the run file of every prototype that the run needs (section 5.2) and that has none yet, reading each section's prose for how it starts. It reads `${CLAUDE_PLUGIN_ROOT}/skills/principle-prove-it-works/SKILL.md` first. `check-run`, then the first commit, with the PR title as its subject. It is not pushed yet. Run files are in the Product Manager's scope (`docs/prototypes/**`).
3. **Run.** `troy_flow.py real-run --item <ID>` on the clean tree.
4. **Open bugs.** When the report's `open_bugs` names open `bug` issues from an earlier real run of this feature, their bug flows come first (section 7.3).
5. **Mismatches.** Exit 1 with mismatches: TM8 rules on all of them in one run (section 7). The Product Manager acts on each ruling, amends any run file or prototype change into the commit under a new snapshot, and goes back to step 3. A command that still mismatches on its third run escalates (5.7, F07 design D64).
6. **Problems.** Exit 1 with `problems` only, such as a run file that names a missing section: the Product Manager fixes the run file and goes back to step 3. A problem with the program or its environment escalates.
7. **Acceptance.** Exit 0: PM3 sets the status from the report's `label` (section 9), raises the requirements' version, and amends. The PR description's Checks section gets the report's one-line summary, and a new section "Real run" holds the report's `description` (section 8). `check-text`, `troy-check pr`, push, open the PR, post the report's `comments` if any, wait for CI, and merge, as now.

Troy sees it in the stage report, in the shape of Prototype B:

```text
[6/6] Real run: 41 commands of 6 prototypes match on your PC. 3 wait for F12.
      Acceptance PR #96 merged. F11 status is now "Ran for real on Troy's PC".
      Not yet checked in Windows Terminal itself or on your devices.
```

## 4. The run file (D103)

### 4.1 Where and why

Each prototype that has a transcript gets a run file next to it: `docs/prototypes/F09-list-show.md` has `docs/prototypes/F09-list-show.run.toml`. The transcript is the script. The run file holds only what the prototype's prose says in words: the data folder each section starts with, the mistakes some sections add to it, and where the prototype's folders are during the run. It is committed in the acceptance PR, so every later run and the release repeat the same steps.

A run file is TOML, not a document: it has no troy-doc header, so it needs no Chinese mirror (R12), and R20 does not scan it. troy-check classes it as `docs`, which PR 6 may change (R02).

### 4.2 Keys

`<home>` is the run's home folder and `<scratch>` the run's scratch folder; `<home>` lies inside `<scratch>`. Paths use Windows' `\` on Windows, in TOML literal strings (`'...'`).

| Key | What it says |
| --- | --- |
| `[paths]` | The path map: each folder the prototype names, and where it is during the run, for example `'C:\Users\Troy' = '<home>'` and `'D:\OneDrive\recipe-menu' = '<scratch>\OneDrive\recipe-menu'`. Every run path starts with `<home>` or `<scratch>`. |
| `[environment]` | `unset`, the variables to remove, such as `["RECIPE_MENU_DATA"]`, and `set`, the variables to add. |
| `[start]` | How every section starts, unless the section says otherwise: `copy`, folders to copy from the repository, such as `[{ from = "tests/data/example", to = '<home>\recipe-menu' }]`; `mkdir`, empty folders to make; and `setup`, commands to run first, such as `["recipe-menu init"]`. A setup command must exit with 0, and its output is not compared. |
| `[programs]` | Only for a command that is not a console script of the project's Python environment: its name and the repository path of the built program, such as `hilog-demo = "build/coverage/hilog-demo"`. |
| `[sections."<heading>"]` | One section of the prototype, named by its heading as written. A heading used twice is `"<heading> (2)"` the second time. |

A section's table may hold:

| Key | What it does |
| --- | --- |
| `start` | `"previous"` to go on from the previous section's folders, `"empty"` for no files, or a table like `[start]` that replaces the default. |
| `replace` | Text edits after the start, such as `[{ file = '<home>\recipe-menu\recipes\mapo-tofu.toml', text = "郫县豆瓣酱", with = "豆瓣酱" }]`. The text must occur exactly once. |
| `write`, `delete` | Files to write with the given text, and files to delete, after the start. |
| `commands` | A typed command line replaced for the run, with its reason, such as `[{ typed = "recipe-menu menu new next", run = "recipe-menu menu new 2026-W47", reason = "next is 2026-W47 on the prototype's date, 10 November 2026" }]` (section 5.6). |
| `later` | Commands that need a feature not accepted yet, such as `[{ feature = "F09" }]` for the whole section or `[{ feature = "F09", typed = "recipe-menu list" }]` for one command (section 6). |
| `skip` | Commands that cannot run through a pipe, with the reason, such as `[{ reason = "edit opens Notepad" }]` (section 10). |
| `files` | Files the program writes, each compared after the section's commands with a fenced block of the section that is not a transcript, such as `[{ path = '<home>\recipe-menu\shopping\2026-W47.md', block = 1 }]`. |

### 4.3 The pilot's fixture

The pilot's prototypes use the data folder that `example-data.md` describes, with 7 recipes and a week menu, while `recipe-menu init` creates only one recipe. The project already holds that folder as test data, `tests/data/example/`, and its tests check it against `example-data.md`. So the run files copy it: `[start] copy = [{ from = "tests/data/example", to = '<home>\recipe-menu' }]`, with `mkdir` for the empty `shopping\` folder. Sections that start before any data folder exists use `start = "empty"`, sections that need `init`'s folder use `setup = ["recipe-menu init"]`, and the F07 prototype's two mistakes are two `replace` edits.

The engine copies a folder from `HEAD`, through git, and only the files git tracks, so the evidence matches its commit. A project with no such folder gets one from the Product Manager under `docs/prototypes/data/`, which is in its write scope.

## 5. The engine command (D102)

### 5.1 Command

```text
python troy_flow.py real-run --item <feature ID> [--keep] [common options]
python troy_flow.py real-run --all [--keep] [common options]
```

`--item` runs the prototypes that the feature's acceptance needs (section 5.2) and decides its label. `--all` runs the prototypes of every accepted feature, for the release test (section 11). `--keep` keeps the scratch folder for a look afterwards. Like every engine command, it never commits, pushes, or writes to GitHub (F07 design D57).

### 5.2 Which prototypes (D105)

The engine reads the requirements' prototypes table (section 3.1 of the requirements template: Prototype, Feature, File) on `HEAD`. It runs every Markdown prototype whose Feature cell names the feature being accepted or an accepted feature, that is, one whose PR 6 has merged. When the requirements have no such table, it takes `docs/prototypes/<feature ID>-*.md`. A listed prototype with no transcript, such as the pilot's `example-data.md`, is reported as having none and needs no run file. A prototype to run without a run file is a problem.

So each acceptance runs the earlier prototypes again on the real program, which takes seconds. The first acceptance after F12 reaches a project writes the run files of the earlier features' prototypes too. In the pilot that is F05, F07, F08, F09, and F10.

The feature's **own commands** are those of the prototypes whose Feature cell names it, except those that wait for another feature (section 6), plus any command, in any prototype, that waits for it. The label depends on them (section 9). Every other command that runs must match too, or the run fails.

### 5.3 Reading a transcript

- **A transcript** is a fenced block whose first line that is not blank starts with `PS> `. Every other block, such as TOML or a saved file, is not run; `files` may compare one.
- **A section** is the nearest heading above the block. Blocks of one section run in order in one state.
- **Input** is each line that starts with `PS> `. **Output** is the lines after it, up to the next `PS> ` line or the end of the block, without blank lines at the end.
- `PS> $LASTEXITCODE` shows the exit code of the command before it: its output's first line is the expected code.
- `PS> $env:NAME = "value"` sets a variable for the rest of the section, after the path map.
- `PS> Get-Content <path>` prints that file from the run, after the path map, and is compared like a command's output.
- `PS> <program> <arguments>` runs the program (section 5.4). The engine splits the arguments at spaces, and keeps text in `"..."` or `'...'` together.
- **Any other line**, such as a pipeline, a redirection, or another PowerShell command, is not run, and the report says so.

### 5.4 The program and its environment (D110)

The first word of a command is the program. In a Python project, it is a console script from `pyproject.toml`'s `[project.scripts]`, run from the project's environment: `<environment>\Scripts\<name>.exe` on Windows, `<environment>/bin/<name>` elsewhere. The environment is `TROY_MODE_ENV_PREFIX` when that is set, as for briefs, or else the folder of `[lang] environment` from `mamba env list --json`. A name in `[programs]` runs that path instead. A program that is not found is a problem, and the report gives its fix, such as `uv pip install -e . --no-deps` in the environment (F06 design 5.4).

Each command runs:

- with the folders of an activated environment first on `PATH`;
- with this checkout's source roots (`[lang] source_roots`) in `PYTHONPATH`, so this commit's code runs even when the environment's editable install points at another checkout. Before the first command, the engine checks this: it imports the console script's package with the same environment and checks that the package lies inside this checkout;
- with `HOME`, `USERPROFILE`, `HOMEDRIVE` and `HOMEPATH`, `APPDATA`, and `LOCALAPPDATA`, and the XDG folders on Linux and macOS, pointing into `<home>`;
- without `PYTHONIOENCODING`, `PYTHONUTF8`, `PYTHONLEGACYWINDOWSSTDIO`, `PYTHONHOME`, and `PYTHONSTARTUP`, which a plain PowerShell does not set and which change how Python writes text;
- with the run file's `[environment]` and the section's `$env:` lines;
- in `<home>`, where a new PowerShell in Windows Terminal starts;
- with an empty standard input, and a time limit of 60 seconds.

### 5.5 Safety

The run never touches Troy's own folders or the repository:

- the scratch folder is new and empty, in the system's temporary folder, and deleted after the run unless `--keep` is given;
- a command, a `$env:` value, or a setup path that holds an absolute path the path map does not cover is not run, and is a problem: on Windows a drive path such as `D:\...` or a network path `\\...`, elsewhere a path that starts with `/`;
- the working tree must be clean, because the evidence names a commit;
- the engine writes its report to `<git dir>/troy-mode/flow/real-run-<item>-<n>.json` and `.md`, and nothing else outside the scratch folder.

It cannot stop a program that writes to a fixed absolute path of its own. The pilot's program finds its data folder from `--data`, `RECIPE_MENU_DATA`, or the home folder, so this does not apply to it.

### 5.6 Comparison (D104)

The real output is compared with the prototype's character for character, after exactly these normalizations, which the evidence lists:

1. CRLF and LF count as the same line end.
2. Spaces and tabs at the end of a line are ignored, because a terminal does not show them.
3. Blank lines at the end of a command's output are ignored.
4. The path map: each run path in the output is shown as the prototype's path, longest first. The scratch folder's long and short spellings, and `\` and `/`, all count.
5. A prototype line that is exactly `...` matches any number of lines.

Nothing else is loosened. The spaces between columns must match exactly, because they are what lines up Chinese text, where each character takes two columns. Dates and numbers must match too.

- **The output** is the standard output, then the standard error. When a command writes to both, the evidence says that the order on screen is not proven.
- **The exit code** is compared when the prototype shows `$LASTEXITCODE`, and recorded always.
- **Text that is not UTF-8** is a mismatch.
- **Words that depend on the day**, such as `this` and `next`, are replaced in the command through the section's `commands`, with the week they mean on the date the prototype states. The output is never edited. Each replacement and its reason are in the evidence.
- **A mismatch** comes with a unified diff of the prototype's lines and the real lines.

### 5.7 The report

| Field | Holds |
| --- | --- |
| `commit`, `program`, `system`, `date` | The code's commit, the program's path and Python version, the Windows version, and the time of the run |
| `prototypes` | Each prototype, its run file, and each section with its start and its commands: the line as typed and as run, the expected and the real output, both exit codes, the result (`matches`, `mismatch`, `waits for <ID>`, or `not run`), the reason, and the diff |
| `counts` | Commands that match, mismatch, wait, and did not run, in all and for the feature's own prototypes |
| `label` | With `--item`: whether the feature gets "Ran for real on Troy's PC" (section 9) |
| `open_bugs` | Open `bug` issues whose titles start with `Real run of <ID>:` (section 7.3) |
| `description` | The "Real run" section for the PR description (section 8) |
| `comments` | The real output split into PR comments, when the section is too long (section 8) |
| `problems` | Run file errors, unmapped paths, a missing program, or a failed check of the code's location |

Exit codes are those of every engine command: 0 when every command that ran matched and there is no problem, 1 when one mismatched or there is a problem, and 2 when the engine could not run.

## 6. Commands that need a later feature (D106)

A prototype may run a command that a later feature builds. The pilot's F05 prototype, for its language and data-folder options, runs `recipe-menu list`, which came with F09. The Product Manager marks such commands in the run file with `later` and the feature's ID.

- The engine checks that the feature exists in the requirements. A command that waits for a feature not yet accepted is reported as `waits for <ID>` and does not count against the label.
- When that feature is the one being accepted, or is accepted, the mark no longer counts: the command runs and must match. Because each acceptance runs the earlier prototypes again (section 5.2), it is checked as soon as it can work, with no list to keep.
- A mark that names an accepted feature is reported as out of date, so the Product Manager can delete it.

Output can point at a later feature too. In the pilot, `recipe-menu show mapo` prints the hint `Run "recipe-menu search mapo" to find it.`, while `search` comes with F10; F09's design calls this an interim state. Such output matches the prototype. The Product Manager reads the real output for hints that name a command or an option of a feature not yet accepted, and lists each with its feature under "Points at later features" in the PR, so Troy knows the hint does not work yet. The later feature's own prototype checks that command.

## 7. Mismatches (D107)

### 7.1 TM8

Every mismatch goes to the Test Manager, because the Product Manager wrote both the prototypes and the run files. One TM8 run rules on all mismatches of a run, with the report in Input (`brief --task TM8 --item <ID> --input-file <file>`). It reads the feature's requirement row, the prototypes and run files involved, the designs of their features, and the rules table. It changes no file, like TM5. Its report is `done`, with one line per mismatch: its kind, the prototype, the section, the command, and the reason.

| Kind | When | What follows |
| --- | --- | --- |
| `bug` | The program does not do what the prototype or the design says | A bug issue and the bug flow (section 7.3). Summary says what the reproduction test must show. |
| `prototype` | A design that Troy approved chose this output on purpose, and the prototype was not updated | The Product Manager updates the prototype in PR 6. The PR lists the change and the design section. |
| `requirement` | The prototype and the design disagree, and Troy has not chosen between them | The requirement change flow (5.4). Troy decides which output stays. |
| `later <ID>` | The command needs a feature not yet accepted | A `later` mark in the run file (section 6) |
| `setup` | The run file sets the section up wrong | The Product Manager fixes the run file. The PR lists every run file change made after the first run. |
| `console` | The command cannot work through a pipe: it reads keys or answers, or opens an editor | A `skip` mark with the reason (section 10) |

A design approved only by the Architect, after Troy's first features (Q2), cannot make a mismatch a `prototype`: that is a `requirement`, so Troy still decides every change to what Troy approved.

### 7.2 Running again

After the rulings, the Product Manager runs `real-run` again. The PR shows only the last run. The bug issues and the listed run file and prototype changes keep the history.

### 7.3 Bugs from a real run

The Product Manager opens one `bug` issue per bug ruling, titled `Real run of <ID>: <summary>`, with the prototype, the section, the command, the commit, the diff, and TM8's Summary. Its number gives the bug ID, as now. TM8 already triaged it, so TM5 does not run. The bug's PR A and PR B are side PRs that interrupt stage 6 (F07 design 8.7): the stage's commit waits unpushed, and after PR B merges the branch is rebased on `origin/main` and the run starts again.

A new session that reaches stage 6 runs `real-run` first. Its `open_bugs` lists the bugs not fixed yet, so the session goes on with their bug flows and opens no second issue for the same mismatch.

## 8. Evidence (D108)

The requirements ask for the real output and its comparison in the PR. The engine writes the PR description's "Real run" section, so the Product Manager copies it rather than retyping it:

| Part | Holds |
| --- | --- |
| Header | The code's commit on `origin/main`, the program and its Python version, the Windows version, the date, and one line: "through pipes, not a console (F12 design section 10)" |
| Result | The counts, for example "41 commands match. 3 wait for F12. None did not run." |
| Commands | One row per command: prototype, section, command as typed, exit code, and result |
| Adaptations | The path map, the replaced commands with their reasons, how each section started, and the five normalizations |
| Changes | Prototype changes in this PR with their design sections, and run file changes made after the first run |
| Points at later features | The Product Manager's list (section 6) |
| Not proven | A short list from section 10 |
| Real output | Per prototype, in a folded `<details>` block, in the transcript's own form: each `PS> ` line, the real output after the path map, and the real exit code, so Troy can read it next to the prototype |

The evidence names the program by its command and its environment's name, not by a local path, and shows the run's paths only after the path map; any other spelling of the scratch folder appears as `<scratch>`. So it holds no folder of Troy's PC or of the session, some of which R19's strict mode refuses.

GitHub refuses a description longer than 65,536 characters. When the section passes 60,000, the real output goes into the report's `comments`, each headed `Real run output, part <n>`, and the section links them. The description and the comments pass `check-text` like any PR text (R19).

The run file is committed and makes the run repeatable. The full JSON report stays in the git folder, for the session. A failed run's diff goes into its bug issue. No output file is committed: it would be a long English document that needs a mirror and adds nothing the PR does not hold.

## 9. The status label (D109)

templates/README.md section 5 gains a row between "Passes tests on main" and "Usable on Troy's devices":

| Label | Set when |
| --- | --- |
| Ran for real on Troy's PC | PR 6 merges with a real run in which the feature's own commands ran on Troy's PC and matched, apart from those that wait for a later feature (F12). |

In Chinese it is "在 Troy 的电脑上真跑过", as in Q12. At least one own command must have run. "Passes tests on main" stays for a PR 6 without that: a feature with no transcript of its own, such as a library; one whose own commands all wait for later features; or one with an own command that cannot run through a pipe. The PR then says why.

- The features table still changes only in PR 6, at version acceptance, and through the change flow. A later real run that passes the prototypes of an earlier feature does not change that feature's label, and one that fails them leads to a bug fix before the current PR 6.
- At the release, PM4 sets "Usable on Troy's devices" as now, which replaces either label.
- The requirements template's Status comment lists the new label too.

## 10. What a pipe can and cannot prove (D111)

The engine runs each command as a child process with pipes, not in Windows Terminal. A real console would take Windows' pseudo console API and much more code, and still not show how Windows Terminal draws the text.

| The run proves | The run does not prove |
| --- | --- |
| The command Troy types starts the program, through its declared entry point, with this commit's code | How Windows Terminal draws the text: the font, whether it gives each Chinese character two columns, colors, and wrapping at the window's width |
| Each prototype command gives the prototype's text, after the five normalizations, and the exit code it shows | What Python does in a real console, where it writes through the console's own text interface rather than bytes |
| The spaces between columns, as the program counts each character's width | The order of standard output and standard error on screen, when a command writes to both |
| The output is UTF-8 without help from Python's encoding variables | How PowerShell itself splits a command line: quotes, empty arguments, and the differences between Windows PowerShell 5.1 and PowerShell 7 |
| The program reads and writes real files in real folders, and the files it writes match where `files` names them | Commands that read keys or answers, or open an editor |
| Earlier features' prototypes still work at this commit | Troy's own install: `uv tool install`, `PATH`, and the Python that uv manages (the pilot's ADR-0006) |
| | `this`, `next`, and other words that depend on the day, when the run file replaced them |

What the run does not prove stays with Troy's test on Troy's devices at the release (5.5) and with the version test plan's scenarios for Troy.

## 11. At the release (D112)

The release test (F08, step 4 of the release) also runs `real-run --all` on the release branch after the version tests. `release-test` gains `--real-run <report>`: its comment, `Release test, run <n>: passed` or `failed`, then has a "Real run" part with the counts, and a mismatch fails the run. A mismatch goes to TM8, and its bug through "Failures and bugs" (F08 D74), as now. The run takes seconds and checks the exact commit that the tag will name. The pilot's version tests start `python -m recipe_menu` with their own setup, so this adds the command Troy types.

## 12. Changes to earlier features

- **F01 templates.** `templates/README.md` section 5 and its mirror gain the label (section 9). The requirements template's Status comment, and its mirror, list it. troy-init's upgrade brings both into a project, because a project does not edit them.
- **F04 roles.** PM3 in `troy-mode/roles/product-manager.md` becomes: write or update the run files, run `real-run`, act on TM8's rulings, then set the status from `label`. `agents/troy-test-manager.md` gains TM8 (section 7.1), in English only (F04 D35). No write scope changes.
- **F05 hooks.** No change. The main session runs the engine. The program writes only into the scratch folder, outside the repository. PM3's snapshot sees only the run files, the prototypes, and the requirements, which are in the Product Manager's scope.
- **F06 troy-init.** No code change. Its upgrade replaces the two changed templates.
- **F07 entry skill.** The engine table gains `real-run`. PR 6's row and section "One stage" gain the steps of section 3. The rulings list gains TM8. Section "Bug fix" says that a real run's bug starts at its issue, triaged by TM8. Section "Comments" gains the heading `Real run output, part <n>`. `brief` gains TM8.
- **F08 release.** `release-test` gains `--real-run`, and the release's step 4 runs `real-run --all` (section 11).
- **F10 guide.** `03-features.md` (PR 6 and what Troy sees), `05-release.md` (the release test), `07-taking-part.md` (the labels), and `08-reference.md` (the run file, the command, and the comment heading), with their mirrors, in the same PR.
- **troy-check.** No change. So `status` does not report the project's copy as old (F07 design 5.1), and the pilot runs the upgrade at Troy's request (section 13).

## 13. How the pilot gets F12 (D113)

1. **Version.** F12's PR raises `version` in `.claude-plugin/plugin.json` by one minor step, as F10 D89 asks for a feature: to 0.3.0, or to the next minor number if another feature's PR, such as F14's, raised it first. Projects get the engine, the skill, and the roles from the plugin itself, and the templates through the upgrade.
2. **Trial and status.** The trial (section 15.3) passes, and F12's status reads "Runs on a sample project".
3. **Install.** Troy runs `claude plugin update troy-pstack@troy-pstack` and restarts Claude Code (F10 section 6).
4. **Upgrade.** At the pilot's next natural stop, after an acceptance PR merges, Troy types `/troy-pstack:troy-mode upgrade troy-mode` in the pilot session. troy-init's `[rules] Upgrade troy-mode to <version>` PR replaces the two templates.
5. **First use.** The next PR 6 runs for real, and writes the run files of the earlier features' prototypes as well (section 5.2).

If the pilot's last v0.1 feature is accepted before step 4, the pilot waits before "release v0.1" until F12 is installed, so the release uses it (Q11). The pilot report says which features had a real run.

## 14. How F12 maps to the requirements

| Requirement | Where F12 covers it |
| --- | --- |
| F12 row: the Product Manager runs every command of the feature's prototype the way Troy would | Sections 3, 5.2, and 5.4 |
| F12 row: the real output and its comparison in the PR | Sections 5.6 and 8 |
| F12 row and 5.2 PR 6: a mismatch goes to the bug flow before acceptance | Section 7 |
| F12 row: command-line projects first, the transcripts are the script | Sections 4 and 5.3 |
| Q12: the label "ran for real on Troy's PC" | Section 9 |
| Q11: during the pilot, before its v0.1 release | Section 13 |
| Q13 and 4.1 `create-verification-skill`: graphical and web projects | Section 16 |
| 4.1 `principle-prove-it-works` | Section 3, step 2 |
| 5.5: the release test on Troy's PC | Section 11 |
| R13: a label says how far a feature really goes | Sections 9 and 10 |
| Section 8: Privacy and Platform | Sections 5.4 and 5.5 |

## 15. How F12 is checked

### 15.1 Tests

A separate agent writes the tests from this design before the code exists, with `unittest`, a temporary git repository, and a small sample program named in `[programs]`, plus a fake environment folder for the console script path. Cases include:

- transcripts: prompts, `$LASTEXITCODE`, `$env:`, `Get-Content`, lines that are not run, `...`, blank lines at the end, sections and repeated headings, and blocks that are not transcripts;
- run files: unknown keys, a section that does not exist, a copy from a folder git does not track, a `replace` text found zero or two times, an absolute path the map does not cover, and `later` naming an unknown feature;
- prototypes: the table, the fallback by file name, accepted features, and the label;
- comparison: line ends, spaces at line ends, the path map in both directions and longest first, `...`, exit codes, text that is not UTF-8, and both streams;
- the environment: the user folders, the unset Python variables, the working folder, and the check that fails when the package lies outside the checkout;
- the report: a description over the limit split into comments, and the exit codes.

### 15.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: exit codes not compared, `...` not handled, the path map applied one way only, `PYTHONUTF8` passed through, an unmapped absolute path run, the label given with a skipped command of the feature's own, a `later` mark that still counts once its feature is accepted, and a copy from the working tree in place of `HEAD`. The counts go in the PR description.

### 15.3 Trial (D114)

Before the PR opens:

1. **The engine on the pilot's prototypes.** In the build session's scratch folder, a fresh clone of `ZJUCao/recipe-menu` at its current `main`, with run files for the prototypes of its accepted features, run with `real-run --all` in the pilot's environment, which it only reads. A probe on 2026-11-14 saw these commands match, Chinese columns included. Then one message is changed in the clone's source, and the report must show the mismatch and its diff, and a command with an unmapped `D:\OneDrive` path must be refused. Nothing in `D:\Troy\Projects\recipe-menu` changes, and nothing is pushed.
2. **The flow on `ZJUCao/troy-mode-trial`**, in nested `claude -p` sessions with troy-pstack loaded from the PR branch, under Troy's standing permission for trials. troy-init's upgrade first. A requirement change adds a small command-line feature with a `PS> ` prototype, for example a `wordcount` command, and takes it through its six PRs. Its console script goes into `pyproject.toml` through the architecture change, which Troy's answers in the prompt accept. A comment of Troy's on its design, given in the trial's prompt, asks for exit code 2 where the prototype shows 1, so PR 6's first real run mismatches and TM8 rules on it. A new session continues in the middle. PR 6 merges with the real run in its description. About 15 role runs and $15 to $25, from F07's to F09's trials, plus a few Actions minutes per PR.

### 15.4 Status

| When | F12's status in requirements 7.2 |
| --- | --- |
| The F12 PR merges after its trial | Runs on a sample project: the engine replayed the pilot's prototypes on a scratch clone and caught a planted mismatch, and troy-mode took a command-line feature of `ZJUCao/troy-mode-trial` through PR 6 with a real run. Not yet used on a real project. |
| The pilot's first PR 6 with a real run merges | Used on a real project: the acceptance PR of <feature> of `ZJUCao/recipe-menu` carried a real run of <n> commands on Troy's PC. |

Each status update is its own PR.

## 16. Not in F12

- Projects with a graphical or web interface. `create-verification-skill` and `maintain-verification-skill` come when the first such project adopts troy-mode (Q13).
- A real console, through Windows' pseudo console API (section 10).
- Transcripts with a `$ ` prompt for a POSIX shell, PowerShell pipelines and scripts, and commands that read input.
- Giving the new label to features accepted before F12 reaches a project.
- Changing the version test plan or the version tests (F08).
- Spot checks of Troy's approvals, which use F12's evidence (F18).

## 17. Decisions for Troy

F11's design ends at D100. F12 uses D101 to D120, and the designs of F13 and F14 start at D121. Troy accepted every recommended answer on 2026-11-14.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D101 | Who runs the real run? | A: the main session, as the Product Manager, through one engine command (section 3). B: the Test Engineer, as a role run. C: a fresh subagent that took no part in the feature. | A. The requirements give acceptance to the Product Manager, and only the main session talks with Troy. F05's hooks do not limit the main session's commands apart from their git and gh guards, and the run writes nothing in the repository, so no hook changes. A role's report would pass the output on second-hand. The engine does the comparison, and the Test Manager rules on every mismatch (D107), so the Product Manager does not judge its own prototypes. |
| D102 | How is the program run and compared? | A: an engine command, `real-run`, replays every command of the transcripts, compares the output, and writes the evidence; the skill writes the run files and acts on the result (section 5). B: the Product Manager runs each command by hand and compares by eye. C: the Test Engineer writes a test for each prototype section. | A. Comparing Chinese columns by eye is easy to get wrong, and a script repeats the same check every time (`principle-prove-it-works`). C writes the prototypes a second time as code, and would start `python -m` rather than the command Troy types. |
| D103 | How does each section get its data folder? | A: a run file next to each prototype, `docs/prototypes/<name>.run.toml`, committed in PR 6: the tracked folder to copy (in the pilot, `tests/data/example/`, which its tests already hold to `example-data.md`), setup commands such as `recipe-menu init`, small text edits, the path map, replaced date words, and the `later` and `skip` marks (section 4). B: the same steps in a file in the git folder, written again for every run and never committed. C: setup lines inside the prototypes themselves. | A. The setup is part of the script, so it should be reviewable and the same at every later run and at the release. The prototypes stay as Troy approved them. With B, later runs cannot repeat the setup. |
| D104 | How exact is the comparison? | A: character for character, after five fixed normalizations: line ends, spaces at line ends, blank lines at the end, the path map, and `...` lines. No tolerance for the spaces between columns, dates, or numbers. A date word such as `next` is replaced in the command, with its reason, never in the output. The exit code is compared where the prototype shows it (section 5.6). B: also treat runs of spaces as one. C: exact bytes, with no normalization. | A. The spaces between columns are what lines up Chinese tables, so they must match exactly. The five normalizations cover only what a terminal hides or what depends on where the run takes place. B would miss wrong alignment, and C fails on every path. |
| D105 | Which prototypes does each acceptance run? | A: the feature's own, and those of every accepted feature, so each acceptance runs the earlier prototypes again on the real program; the first acceptance with F12 writes their run files (section 5.2). B: only the feature's own. | A. It takes seconds, finds a later feature that breaks an earlier one in the way Troy uses it, and makes a waiting command run as soon as its feature lands. In the pilot it also checks F05 to F10 before the release. Their labels stay as they are (D109). |
| D106 | What about prototype commands that need a later feature? | A: a `later` mark with the feature's ID in the run file. The command is reported as waiting and runs as a normal command once that feature is being accepted or is accepted. Output that names a later feature's command, such as the hint for `search` before F10, matches, and the PR lists it under "Points at later features" (section 6). B: skip such commands for good. C: accept no feature whose prototype needs a later one. | A. The pilot's F05 prototype runs `list`, which came with F09. B would never check those commands, and C would have blocked F05. A checks every command as soon as it can work. |
| D107 | What happens on a mismatch? | A: one run of a new Test Manager task, TM8, rules on every mismatch of a run: a bug (an issue `Real run of <ID>: ...` and the bug flow's two PRs), a prototype out of date (only when a design Troy approved chose that output; the prototype is updated in PR 6), a requirement question for Troy (the requirement change flow), a later feature, a run file mistake, or a command that needs a console. Then the run starts again, and a command that still mismatches on its third run escalates (section 7). B: the Product Manager decides. C: every mismatch is a bug. | A. The Product Manager wrote the prototypes and the run files, so another role should rule on them, and the Test Manager already triages bugs. C would change code to match a prototype that an approved design changed on purpose. A design Troy did not approve never overrides a prototype Troy did. |
| D108 | Where does the evidence go? | A: the acceptance PR's description, in a "Real run" section that the engine writes: the commit, the program, the system, the counts, a row per command, the adaptations, what the run cannot prove, and the real output folded per prototype; output over GitHub's limit goes into PR comments. The run file is committed, the full report stays local, and a failed run's diff goes into its bug issue (section 8). B: also a committed evidence file per feature, with a Chinese mirror. C: the description only, with no run file. | A. The requirements ask for the evidence in the PR, and GitHub keeps it. The run file makes it repeatable. B adds a long document of program output that needs a mirror and holds nothing the PR does not. C cannot be repeated. |
| D109 | When does a feature get "Ran for real on Troy's PC"? | A: when every command of its own prototypes ran and matched, apart from commands that wait for a later feature. Otherwise it gets "Passes tests on main", and the PR says why. Earlier features keep their labels, and the release still sets "Usable on Troy's devices" (section 9). B: a partial label, such as "Ran for real on Troy's PC, 12 of 14 commands". C: also give the label to earlier features whose prototypes pass in a later run. | A. A label says how far a feature really goes (R13), and one short label is the easiest to read. The PR gives the counts. C would change the status table outside PR 6 and the release. |
| D110 | Which program does the run start? | A: the command Troy types, found in the project's development environment (for Python, the console script from `pyproject.toml`), running this checkout's code, which the engine checks first. Troy's folders are replaced by a scratch home, Python's text-encoding variables are removed, and a command with a folder the path map does not cover is refused (sections 5.4 and 5.5). B: install the checkout the way Troy installs a release, with `uv tool install`. C: `python -m <package>`. | A. It is the same entry point Troy types, with this commit's code, and nothing of Troy's own install or data is touched. B would replace Troy's installed `recipe-menu`. C skips the entry point. |
| D111 | Does the run use a real console? | A: no, pipes. Section 10 lists what that cannot prove, which stays with Troy's test on Troy's devices at the release. B: a real console through Windows' pseudo console API. | A. B is much more code, works on Windows only, and still does not show how Windows Terminal draws the text. Pipes catch the common problems: wrong text, wrong column widths, wrong exit codes, and wrong files. |
| D112 | Does the release test run the prototypes too? | A: yes, `real-run --all`, and a mismatch fails the release test (section 11). B: no, only acceptance PRs run them. | A. It takes seconds and checks the exact commit that gets the tag. The pilot's version tests start `python -m` with their own setup, so this adds the command Troy types. |
| D113 | How does the pilot get F12? | A: F12's PR raises the plugin's minor version, to 0.3.0 or the next free minor number. After the trial and the status PR, Troy updates the plugin and restarts Claude Code, then types `/troy-pstack:troy-mode upgrade troy-mode` in the pilot at its next natural stop. The next PR 6 runs for real. If the pilot's last feature is accepted first, it waits before "release v0.1" (section 13). B: as A, with a patch version, 0.2.1. C: after the pilot. | A. F10 D89 gives a feature the minor number and a fix the patch number. Q11 asks for F12 before the pilot's v0.1 release. Without the upgrade, the project's templates would lack the new label. |
| D114 | How is F12 tried before its PR? | A: the engine on a scratch clone of the pilot's repository, with one planted change of a message, then the flow on `ZJUCao/troy-mode-trial`: a command-line feature through its six PRs, where a comment of Troy's makes the first real run mismatch and TM8 rule on it; about 15 role runs and $15 to $25 (section 15.3). B: only the engine on the clone; the pilot is the first run of the flow. C: only the flow trial. | A. The clone tests the engine on real prototypes without touching the pilot, and the flow trial tests the new steps of PR 6 before the pilot depends on them, as every feature since F07 was tried. B is faster but makes the pilot the trial. |

Requirements 1.35 records the approved changes:

- The F12 row says what F12 builds (D101 to D114).
- Section 4: the Test Manager also rules on the mismatches of a real run (D107).
- 5.2, PR 6: the run file (D103); the real run of the prototypes of the feature and of every accepted feature (D102, D105); the Test Manager's ruling on each mismatch (D107); the evidence in the PR description (D108); and when the new label applies (D109).
- 5.3: a bug from a real run is triaged by that ruling (D107).
- 5.5: the release test runs the prototypes of every accepted feature too (D112). 5.6 lists the real run at each acceptance and each release test.

## 18. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-14 | First draft. |
| 1.0 | 2026-11-14 | Approved by Troy with D101 to D114, every recommended answer. |
