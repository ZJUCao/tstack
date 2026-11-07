# F02 design: language-independent checks

| | |
| --- | --- |
| Feature | F02 in [requirements 1.3](../requirements.md#72-feature-list) |
| Version | 1.2 |
| Date | 2026-11-07 |
| Status | Approved by Troy on 2026-11-05, with D7 to D14 |
| Source of truth | This English file. [`F02-checks.zh-CN.md`](F02-checks.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F02 delivers one command-line tool, `troy-check`, and a GitHub Actions workflow that runs it on every PR of a troy-mode project. The tool checks the rules that do not depend on the project's language:

| Rule | What F02 checks |
| --- | --- |
| R01 | The PR has exactly one commit. |
| R02 | The PR title names a known kind (F01 design D1), and every changed file belongs to a class that kind may change. |
| R03 | A source PR changes at most 500 lines in at most 5 files, or its description gives a reason. |
| R12 | Each changed English document raised its version, and its Chinese mirror matches it. |
| R16 | Changed dependency files are flagged for the Architect. |
| R19 | Commit emails are right, and no commit message, PR title, or PR description carries Claude attribution. |
| R20 (new, D11) | No changed document and no PR description still holds template markers or guidance (F01 design D2). |

It also offers a `commit` subcommand that checks R19 for one commit before it is made. F05's hooks use it.

F02 does not copy anything into projects (F06), run language-specific checks (F03), or decide when Claude merges (F07).

## 2. Location

In troy-pstack, beside F01's templates:

```text
troy-mode/
  checks/
    troy_check.py          entry point
    troycheck/             internal modules (the Developer's choice)
    config.default.toml    commented copy of the defaults in section 7
    workflow.yml           the workflow in section 8
    tests/                 unit tests (section 10)
```

In a project, `troy-init` (F06) copies the folder to `.troy-mode/checks/` and the workflow to `.github/workflows/troy-mode.yml` (D8). The project's own settings live in `.troy-mode/config.toml`.

## 3. Command-line interface

The tool runs with Python 3.11 or newer and uses only the standard library (D7). On Windows it runs as `python`, on Linux and macOS as `python3`.

### 3.1 `pr`

Checks a whole PR. troy-mode runs it before each push. CI runs it on every PR event.

```text
python .troy-mode/checks/troy_check.py pr --base <ref> [--head <ref>] --title <text> [--body-file <path>] [--repo <path>] [--json]
```

| Option | Meaning |
| --- | --- |
| `--base` | The target branch, for example `origin/main` or a commit SHA. The PR's changes are the commits from the merge base of `--base` and `--head` to `--head`. |
| `--head` | The PR's last commit. Default `HEAD`. |
| `--title` | The PR title. |
| `--body-file` | A UTF-8 file with the PR description. Without it, R03 sees no soft-limit reason and R20 skips the description. |
| `--repo` | The repository root. Default: the git top level of the current folder. |
| `--json` | Print the JSON report (section 3.3) in place of the text report. |

It reads `.troy-mode/config.toml` from the merge-base commit, not from the PR. A PR cannot loosen the rules that judge it. A rule change takes effect on the PRs after it.

### 3.2 `commit`

Checks R19 for one commit before it exists.

```text
python .troy-mode/checks/troy_check.py commit (--message-file <path> | --message <text>) [--email <address>] [--repo <path>] [--json]
```

| Option | Meaning |
| --- | --- |
| `--message-file`, `--message` | The commit message. |
| `--email` | The author email to check. Default: the email in `git var GIT_AUTHOR_IDENT`, which is what git will use. |
| `--repo`, `--json` | As in `pr`. |

It reads `.troy-mode/config.toml` from the working tree. It also works as a git `commit-msg` hook: `python .troy-mode/checks/troy_check.py commit --message-file "$1"`. F05 decides which hooks call it.

### 3.3 Report and exit codes

Each rule ends in one of four results:

| Result | Meaning |
| --- | --- |
| `pass` | The rule holds. |
| `warn` | The PR may merge, but someone must look: a soft limit passed with a reason, or a dependency file changed. |
| `fail` | The PR must not merge. |
| `skip` | The rule does not apply to this kind of PR. |

Text report:

```text
troy-check pr: [F04 5/6 impl] Export history as CSV
Kind: impl, feature F04, stage 5/6. May change: source, dependencies.
pass  R01  1 commit.
pass  R02  4 files, all source.
warn  R03  612 changed lines in 4 files, over 500. Reason given: "Splits storage.py."
skip  R12  No documents changed.
warn  R16  Dependency files changed. Needs the Architect's approval.
      pyproject.toml
pass  R19  1 commit by 148482542+ZJUCao@users.noreply.github.com. No attribution.
pass  R20  No template markers.
Result: pass, 2 warnings.
```

JSON report (`--json`):

```json
{
  "command": "pr",
  "ok": true,
  "title": {"kind": "impl", "id": "F04", "stage": "5/6", "summary": "Export history as CSV"},
  "results": [
    {
      "rule": "R16",
      "result": "warn",
      "message": "Dependency files changed. Needs the Architect's approval.",
      "details": [{"path": "pyproject.toml", "line": null, "message": "changed"}]
    }
  ]
}
```

`ok` is false when any result is `fail`. `title` is null when the title does not parse, and for `commit`.

When the environment variable `GITHUB_ACTIONS` is `true`, the tool also prints one GitHub annotation per `fail` or `warn` detail (`::error file=<path>,line=<n>::R12 ...`) and appends the text report to `$GITHUB_STEP_SUMMARY`. With `--json`, the annotations go to stderr, so stdout stays valid JSON.

| Exit code | Meaning |
| --- | --- |
| 0 | No `fail`. |
| 1 | At least one `fail`. |
| 2 | The tool could not run: bad options, not a git repository, a git error, or an invalid config file. |

## 4. PR titles

The title grammar from F01 design D1, made exact. Spaces are single. IDs and stage names are case-sensitive. The summary is at least one character that is not a space.

| Kind | Pattern | Example |
| --- | --- | --- |
| Feature stage | `[<F-ID> <n>/6 <stage>] <summary>`, with `<n>` and `<stage>` one of: 1 `design`, 2 `test-plan`, 3 `mock`, 4 `tests`, 5 `impl`, 6 `accept` | `[F04 3/6 mock] Export history as CSV` |
| Bug test | `[<B-ID> A/B test] <summary>` | `[B12 A/B test] Crash on empty history` |
| Bug fix | `[<B-ID> B/B fix] <summary>` | `[B12 B/B fix] Crash on empty history` |
| Test fix | `[<F-ID or B-ID> test-fix] <summary>` | `[F04 test-fix] Wrong date format in F04-T03` |
| Other | `[docs] <summary>`, `[rules] <summary>`, `[refactor] <summary>` | `[rules] Add P01, no global state` |

`<F-ID>` is `F` and two or three digits. `<B-ID>` is `B` and a GitHub issue number. A title that matches no pattern fails R02, and R03 is skipped.

## 5. Path classes (R02)

Each changed path gets exactly one class. The first class in this order whose patterns match wins:

| Order | Class | Built-in patterns | Added by |
| --- | --- | --- | --- |
| 1 | `config` | `.troy-mode/**`, `.github/**`, `docs/rules.md`, `docs/rules.zh-CN.md`, `.gitignore`, `.gitattributes`, `.editorconfig` | Project config |
| 2 | `dependencies` | None | Language packs (F03), project config |
| 3 | `tests` | `tests/**`, `test/**` | Language packs (F03), project config |
| 4 | `docs` | `docs/**`, `**/*.md`, `LICENSE*` | Project config |
| 5 | `source` | Everything else | None |

Patterns match the whole path from the repository root, with `/` separators. `*` matches within one folder name, `**` matches any number of folders, and `?` matches one character.

What each kind may change (D9):

| Kind | Allowed classes |
| --- | --- |
| `design`, `test-plan`, `accept`, `docs` | `docs` |
| `mock`, `impl`, `fix`, `refactor` | `source`, `dependencies` |
| `tests`, `test` (bug A), `test-fix` | `tests`, `dependencies` |
| `rules` | `config`, `dependencies` |

A renamed file is checked under both its old and its new path. R02 fails once per path whose class the kind may not change.

## 6. Checks

All checks compare the merge base with `--head`. "Changed" means added, modified, deleted, or renamed.

### 6.1 R01: one commit

Counts the commits from the merge base to `--head`, merge commits included. Exactly one passes. Otherwise R01 fails and lists the commits.

### 6.2 R02: one stage

Parses the title (section 4), classifies every changed path (section 5), and fails for each path the kind may not change.

### 6.3 R03: source PR size

Applies to `mock`, `impl`, `fix`, and `refactor`. Skipped for other kinds.

- Lines are added plus deleted lines from `git diff --numstat --find-renames`. A binary file counts as 0 lines.
- Files matching the `lock` or `generated` patterns (section 7) count neither lines nor files.
- Over 500 lines or over 5 files: `warn` if the description's "Soft-limit reason" section gives a reason, `fail` if not.
- The reason is the section's text with HTML comments removed. Empty text, `None`, `None.`, and `无` mean no reason.

### 6.4 R12: English and Chinese mirrors

A document is a `.md` file that starts with front matter holding `troy-doc` (F01 design section 4). Files under `.troy-mode/` are not documents: troy-init copies the templates there, and their headers hold markers and share `troy-doc` IDs with the project's documents on purpose (F06 design section 8). For each changed document:

1. The header is valid: `troy-doc`, `lang`, `version`, `updated`, and `status` exist. `lang` is `en` or `zh-CN`. An English document has `mirror`, and a Chinese one has `mirror-of`. Every value is in double quotes. `version` is `MAJOR.MINOR`. `updated` is `YYYY-MM-DD`.
2. Its partner exists in the same folder, and `mirror` and `mirror-of` point at each other.
3. Both have the same `troy-doc` and the same `version`.
4. A modified English document has a higher `version` than at the merge base. A new English document arrives with its mirror.
5. Deleting an English document also deletes its mirror.
6. Both have the same sequence of heading levels and the same column counts in the same tables, outside code blocks (D12).

A Chinese-only change passes when points 1 to 3 and 6 hold. That allows translation fixes.

Across the whole repository at `--head`, no two English documents share a `troy-doc`.

### 6.5 R16: dependency files

Lists every changed path in the `dependencies` class as a `warn`. It never fails. The Architect's review is the gate.

### 6.6 R19: commit identity and attribution

For every commit in the PR:

- The author email equals `commit_email` in the config.
- The committer email equals `commit_email`, or is `noreply@github.com`, which GitHub uses for commits made in its web interface.

For every commit message, the PR title, and the PR description, R19 fails on Claude attribution:

- Always: a `Co-Authored-By:` line that names Claude or an `anthropic.com` address, the text "Generated with Claude Code", a link to `claude.com/claude-code` or `claude.ai/code`, or the address `noreply@anthropic.com`.
- In `strict` mode, the default (D10): any whole word `Claude` or `Anthropic`, in any case. This matches Troy's global CLAUDE.md, which allows no mention of Claude in commits or PRs.

Without a `commit_email` in the config, the email part is a `warn` that says so.

### 6.7 R20: template markers (D11)

Fails for every template marker or guidance comment left in a changed document or in the PR description:

- A marker is `{{` not preceded by `$`, then text with no braces and no line break that neither starts nor ends with a space, then `}}`. Every F01 marker has this shape, for example `{{feature-id}}`. Code that puts spaces inside the braces, as GitHub Actions (`${{ github.sha }}`), Vue, and Jinja usually do, does not match. Neither do C++ brace initializers such as `{{1, 2}, {3, 4}}`.
- A guidance comment is `<!--`, optional spaces, then `template:`.

Code blocks are scanned too, because templates put markers in them. Files under `.github/` and `.troy-mode/` are not scanned, because the PR template and the copied templates hold markers on purpose. A file in `allow_markers` is not scanned.

Each failure gives the path and line.

## 7. Project config

`.troy-mode/config.toml`. Every key is optional. Lists add to the built-in patterns and never replace them. An unknown key or a wrong type stops the tool with exit code 2, so a typo never turns a rule off.

```toml
[identity]
commit_email = "148482542+ZJUCao@users.noreply.github.com"  # R19. troy-init fills it in.

[paths]
config = []         # added to the config class
dependencies = []   # language packs add manifests, for example "pyproject.toml"
tests = []          # language packs add patterns, for example "**/test_*.py"
docs = []
lock = []           # not counted by R03, for example "uv.lock"
generated = []      # not counted by R03
allow_markers = []  # documents that hold {{ }} on purpose

[limits]
source_lines = 500  # R03
source_files = 5    # R03

[attribution]
mode = "strict"     # "strict" or "trailers" (D10)
```

## 8. GitHub Actions workflow

`troy-mode/checks/workflow.yml`, which `troy-init` copies to `.github/workflows/troy-mode.yml`:

```yaml
name: troy-mode checks
on:
  pull_request:
    types: [opened, edited, synchronize, reopened]
permissions:
  contents: read
jobs:
  troy-check:
    name: troy-mode checks
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@<full commit SHA>
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0
      - name: Run troy-check
        env:
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
          PR_TITLE: ${{ github.event.pull_request.title }}
          PR_BODY: ${{ github.event.pull_request.body }}
        run: |
          checks=.troy-mode/checks
          if git cat-file -e "$BASE_SHA:$checks/troy_check.py" 2>/dev/null; then
            mkdir -p "$RUNNER_TEMP/base"
            git archive "$BASE_SHA" "$checks" | tar -x -C "$RUNNER_TEMP/base"
            checks="$RUNNER_TEMP/base/$checks"
          fi
          printf '%s' "$PR_BODY" > "$RUNNER_TEMP/pr-body.md"
          python3 "$checks/troy_check.py" pr --base "$BASE_SHA" --head "$HEAD_SHA" \
            --title "$PR_TITLE" --body-file "$RUNNER_TEMP/pr-body.md"
```

- `edited` reruns the checks when the title or description changes.
- It runs the checker from the base commit when one exists there, so a PR cannot change the code that judges it. The first PR that adds the checker runs its own copy.
- The title and description reach the shell only through environment variables, never pasted into the script, so a crafted title cannot run commands.
- It uses `pull_request`, never `pull_request_target`, and reads the repository only.
- The job name `troy-mode checks` stays fixed, so it can be made a required check (D14).

## 9. Non-functional requirements

- **Platform.** Windows 11, Linux, and macOS. Paths are handled with `/`. Files are read as UTF-8, and output is UTF-8 whatever the console code page, so Chinese text survives a Chinese-locale Windows console.
- **Speed.** `commit` finishes in under 200 ms, the hook budget. `pr` finishes in under 5 seconds on a repository with 1,000 files and a 50-file PR.
- **Safety.** The tool reads git objects and files. It never runs code from the repository and makes no network call.
- **No environment.** The tool uses only the standard library, so it needs no environment and no package install. Any Python 3.11 or newer on the PATH runs it. Python projects' own environments, managed with mamba and uv (requirements section 8), are F03's concern.
- **Code rules.** The tool's own code follows R04 to R06 and Google-style doc comments, although troy-pstack is not a troy-mode project.

## 10. How F02 is tested

Tests are written first, in the same PR (requirements Q10). They use `unittest`, so nothing needs installing: `python -m unittest discover -s troy-mode/checks/tests`. Each test builds a small git repository in a temporary folder.

| Group | Cases include |
| --- | --- |
| Titles | Every kind parses. Stage number and name that disagree. Missing summary. Lowercase ID. Double space. |
| R01 | One commit. Two commits. A merge commit counts. |
| R02 | A source file in a docs PR. A dependency file in a tests PR. A rename across classes. An unknown title. |
| R03 | 500 lines pass and 501 fail. 501 with a reason warn. A sixth file. Lock files not counted. A binary file. A docs PR skipped. |
| R12 | Version not raised. Mirror not changed. Versions differ. Pointers wrong. New English without mirror. Heading levels differ. Table columns differ. Unquoted value. Chinese-only fix passes. English deleted alone. Duplicate `troy-doc`. |
| R16 | Manifest changed warns. No manifest passes. |
| R19 | Wrong author email. GitHub committer allowed. `Co-Authored-By` trailer. A bare word in strict mode. The same word in trailers mode. No email configured. |
| R20 | Marker with line number. Guidance comment. C++ brace initializer passes. `${{ github.sha }}` and `{{ count }}` pass. `allow_markers`. Marker in the description. `.github/` not scanned. |
| CLI | Exit codes 0, 1, 2. JSON shape. GitHub annotations. Config read from the merge base. Unknown config key. |
| `commit` | Message file. Author email from `git var`. |

troy-pstack gets a workflow, `.github/workflows/troy-checks-tests.yml`, that runs these tests on Linux and Windows for every PR that changes `troy-mode/checks/` (D13).

When F02 merges, its status becomes "Written". It moves on to "Runs on a sample project" once its workflow has run on a throwaway project's PRs. F06's troy-init is what makes that easy.

## 11. Not in F02

- Language-specific checks: R04 to R07, R09 to R11 (F03).
- Copying the checks and the workflow into a project, filling in `commit_email`, and making the check required (F06).
- Claude Code hooks (F05).
- Stage order, for example that PR 1 and PR 2 merged before PR 3, and whether a feature or bug ID exists (F07).

## 12. Decisions for Troy

D1 to D6 belong to the F01 design. F02 continues from D7. Troy approved all eight proposals on 2026-11-05.

| ID | Decision | Proposal |
| --- | --- | --- |
| D7 | Language of the checks. | Python 3.11 or newer, standard library only, tests with `unittest`. Python is on every GitHub runner and on your PC, and it is your first language pack. TypeScript would need Node in every project, C/C++ ones included. Bash is weak on Windows and at parsing. |
| D8 | How a project gets the checks. troy-pstack is private, so CI in another repository cannot read it without a token. | `troy-init` copies the checks into `.troy-mode/checks/` and records the plugin version. The copy also pins the rules each project runs. Rerunning `troy-init` in a `[rules]` PR upgrades it (F06). |
| D9 | Which files each PR kind may change. F01 left this to F02. | The path classes and the table in section 5. Dependency files may change in source, test, and rule PRs. `test-fix` also takes a bug ID, as in `[B12 test-fix]`. |
| D10 | How strict R19 is. Requirements R19 says "no Claude attribution". Your CLAUDE.md also forbids any mention of Claude. | `strict` by default: no word Claude or Anthropic in commit messages, PR titles, or PR descriptions. A project about Claude, for example one that calls the Claude API, sets `mode = "trailers"`. R19's text in the requirements and the rules template changes to match. |
| D11 | The template marker check (F01 D2) has no rule ID, so the report cannot name it. | Add rule R20: "A merged document or PR description holds no template markers or template guidance." Hard, enforced by CI. This adds the PR description to D2. The requirements and the rules template gain R20. |
| D12 | R12 as written checks only the header. A mirror can match the version and still miss a new section. | R12 also compares heading levels and table column counts (section 6.4, point 6). |
| D13 | The checks' own tests need to run somewhere. troy-pstack has no CI. | Add `.github/workflows/troy-checks-tests.yml` to troy-pstack, running on Linux and Windows. It is a new file. No upstream file changes. |
| D14 | What "Hard" means on GitHub. A failed check blocks a merge only when branch protection marks it required, and private repositories get branch protection only on a paid GitHub plan. | troy-mode never merges a PR whose checks fail (F07), on any plan. When the repository allows it, `troy-init` also marks `troy-mode checks` as required (F06). Troy's GitHub plan is free (2026-11-05), so for now troy-mode's merge step is the only gate, and `troy-init` leaves the setting off. |

Requirements 1.3 records the approved changes:

- The F02 row adds R20 and the `commit` subcommand.
- R19's text changes (D10), and R20 is added to section 6 and the rules template (D11).
- Section 6 says that troy-mode's merge step enforces Hard rules (D14).

F02's status becomes "Written" when the F02 PR merges.

## 13. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-05 | First draft. |
| 1.0 | 2026-11-05 | Approved by Troy with D7 to D14. D14 records Troy's free GitHub plan. Section 9 notes that the tool needs no Python environment. |
| 1.1 | 2026-11-05 | Section 3.3: with `--json`, annotations go to stderr. Found while implementing. |
| 1.2 | 2026-11-07 | Section 6.4: files under `.troy-mode/` are not documents for R12, as R20 already does not scan them. Otherwise the templates troy-init copies there fail every setup PR and every later document PR. Found while building F06, approved by Troy on 2026-11-07. |
