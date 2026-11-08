# F10 design: troy-pstack's documentation for troy-mode

| | |
| --- | --- |
| Feature | F10 in [requirements 1.26](../requirements.md#72-feature-list) |
| Version | 1.0 |
| Date | 2026-11-08 |
| Status | Approved by Troy on 2026-11-08, with D86 to D92. |
| Source of truth | This English file. [`F10-docs.zh-CN.md`](F10-docs.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F10 documents troy-mode inside troy-pstack, so that Troy can install it, start a project, and run every flow from the documents alone. It delivers:

1. a troy-mode section in the repository's `README.md` (section 3);
2. a usage guide in English and Chinese, in `docs/troy-mode/guide/` (section 4, D86);
3. a note, in the README section and in the guide, that troy-mode is Troy's own work and not part of Lauren Tan's pstack (section 3.2, D88);
4. a new plugin version, so that an installed troy-pstack picks up troy-mode (section 6, D89);
5. a link check for troy-pstack's own documents (section 9.1, D90).

The guide describes troy-mode as it is built when F10 lands: F01 to F07, plus the version release flow (F08) and the rule change flow (F09). So F10 is built after F09 merges (D91). The pilot (F11) is the guide's first real reader: Troy follows it on a real project, and F11 fixes what it gets wrong.

F10 adds no skill, agent, hook, or engine command, and changes no behavior of troy-mode. It lands in one PR, as Q10 says for every feature.

## 2. Location

```text
README.md                         gains the section "troy-mode" (section 3)
.claude-plugin/
  plugin.json                     version 0.2.0 and a new description (section 6)
  marketplace.json                the plugin's description (section 6)
docs/
  troy-mode/
    guide/
      README.md                   the guide's first page (section 4)
      README.zh-CN.md             and a Chinese mirror for every page
      01-install.md ... 09-changing-troy-mode.md
troy-mode/
  dev/
    check_links.py                the link check (section 9.1)
    tests/
      test_check_links.py         its unit tests
.github/
  workflows/
    troy-docs.yml                 runs check_links.py after check_pairs.py
```

Upstream's guide in `docs/guide/` is Lauren Tan's, adapted for Claude Code. F10 does not change it. Requirements section 8 lets troy-mode touch only three shared files, `README.md`, `plugin.json`, and `marketplace.json`, and F10 keeps to them.

## 3. The README section

### 3.1 Where and what

A new section `## troy-mode` goes after "Get started" and before "How the port works". It is in English only (D87). It holds:

- **The note** of section 3.2.
- **What troy-mode is**, in three sentences: a fixed pipeline of roles that takes a project from requirements to a released version, with each role in its own context, reviewed by another role, and the rules enforced by checks.
- **Quick start**: the two commands Troy types, `/troy-pstack:troy-init` once per project and `/troy-pstack:troy-mode <request>` for all work, and the five steps where troy-mode waits for Troy (requirements 3.3).
- **troy-mode or poteto-mode**: the table of requirements 3.2, shortened.
- **What it adds to the plugin**: the skills `troy-init` and `troy-mode`, the six `troy-*` agents, the hooks in `hooks/hooks.json`, and the files under `troy-mode/`. The skill table further down stays as it is: it records the port of upstream's skills, and troy-mode's parts are not a port.
- **Links**: the guide in English and in Chinese, the requirements, and the designs.

"Make it yours" now says that troy-mode is Troy's own mode, built in this fork, and links to the section. Its old text suggested drafting a troy-mode skill with `automate-me`, which is no longer the plan.

### 3.2 The note (D88)

The README section and the guide's first page start with this note, and the Chinese guide has its translation:

> **troy-mode is Troy's own work.** Troy designed it and built it in this fork. It is not part of Lauren Tan's pstack, and Lauren Tan and Cursor have not reviewed or endorsed it. It reuses pstack skills such as `how`, `why`, `interrogate`, and `correct` without changing them, and it does not change how `poteto-mode` behaves. It is under the same MIT License as the rest of troy-pstack.

The README's existing credit section stays as it is: almost every skill, playbook, agent, and guide page outside troy-mode is Lauren Tan's work.

## 4. The guide

### 4.1 Pages

Every page has a Chinese mirror with the sync header of requirements R12, so `check_pairs.py` checks each pair.

| Page | What it covers |
| --- | --- |
| `README.md` | The note (section 3.2). What troy-mode is, and the one thing to remember: type `/troy-pstack:troy-mode` and what you want, and it stops only where it needs you. The pages, in reading order. |
| `01-install.md` | What Troy's PC needs: Git for Windows with Git Bash, `gh` signed in to GitHub, Python 3.11 or newer for troy-mode's engines, and Miniforge (mamba) with uv for Python projects. Installing troy-pstack from its folder, and updating it after a new plugin version. The permission that lets troy-mode merge its PRs (section 4.3). Models and effort per role, and `[roles]` in `.troy-mode/config.toml` to change them in one project. |
| `02-start.md` | Starting a project: `/troy-pstack:troy-mode start a project: <idea>` in a new or existing folder, or `/troy-pstack:troy-init` alone. troy-init's setup PR and its questions: the private GitHub repository and files it did not write. The Product Manager's questions and the requirements, which Troy approves in chat or by merging on GitHub. The architecture, the environment's series, and the language step. A project that already has code (Q6): its tests are listed as legacy, and old code is checked only when it changes. The files troy-mode adds to a project. |
| `03-features.md` | The feature loop: the requests "next feature", "F04", "F04 to F06", and "the rest of v0.1"; how far one request goes (F07 D63); the six PRs and what each holds; what Troy sees after each stage; approving PR 1 and PR 2 of the first features, and the question after them (F07 D62); reviews, rounds, and attempts; the side PRs for a disputed test, a coverage gap, and a new dependency; performance tests on Troy's PC. |
| `04-bugs-and-changes.md` | Bugs: "bug: ..." or "fix #12", and the bug's two PRs. Requirement changes: "change: ...", Troy's approval, features that need rework, and a change to an accepted feature that becomes a new feature (F07 D65). Questions and experiments, which open no PR. |
| `05-release.md` | The version test plan before a version's first feature (F08 D70). "Release v0.1": the version tests, the release PR, the release test on Troy's PC, and Troy's test on Troy's devices, with the three replies Troy can give (F08 section 5.6). Open bugs and deferring one. Acceptance, the statuses, and the GitHub release. Patch releases. The retrospective, and picking rules from it. |
| `06-rules.md` | "Add a rule ...": the Architect's proposal, Troy's one answer that approves the rule and chooses what happens to existing code (F09 D82), the baseline and the cleanup PRs, changing and retiring a rule, adjusting a troy-mode rule such as R03's limit, and a rule for every project, which becomes an issue in troy-pstack on Troy's yes (F09 D83). |
| `07-taking-part.md` | Where Troy takes part: the five steps of requirements 3.3, and how to answer an escalation (Prototype C). What troy-mode does alone: its merge rights (R18, F07 D61 and D62), the other actions of F07 section 9, the GitHub release after Troy accepts a version, and nothing outside the project without Troy's yes. The feature status labels a project uses (F01 section 7, R13). Continuing in a new session (5.10): the progress file, and "continue". |
| `08-reference.md` | Every request troy-mode understands, with its flow. PR titles and branches by kind. The headings of troy-mode's PR comments. The files in a project, and who may change each. The config keys. Rules R01 to R21, one line each, with a link to the rules template. Problems and what fixes them: a refused merge, a hook that blocked a role, a test that runs on one platform only (F07 D69), Windows path lengths, and a project copy of troy-mode older than the plugin. |
| `09-changing-troy-mode.md` | For work on troy-mode itself in troy-pstack: where the requirements and designs live; the build process (a design Troy approves, tests written from the design by a separate agent, planted bugs, a trial, then a status PR); the checks to run before a push; trials on `ZJUCao/troy-mode-trial` under Troy's standing permission (section 4.4); who merges troy-pstack's PRs; and releasing a new plugin version (section 6). |

The build may split or join pages when the text reads better, as long as the table's content stays and every page keeps its mirror.

### 4.2 How the pages are written

- **Requests are written as Troy types them.** The English pages give English requests. The Chinese pages give the same requests in Chinese, because troy-mode talks with Troy in Troy's language (F07 section 2).
- **Examples come from real runs.** What troy-mode says after a stage, a release test, or a rule proposal is quoted, shortened, from the trial logs of F07, F08, and F09 on `ZJUCao/troy-mode-trial`, with links to the trial PRs. The prototypes of requirements 3.4 are text mocks, so the guide does not reuse them as output.
- **One source for each fact.** A page that states a rule, a limit, or a decision links to the requirement or design that sets it, so a later change has one place to update. Commands, titles, headings, and paths are copied from the skills and engines, not retyped from memory.
- **Status words follow R13.** The guide never calls a flow done or ready for more than its status says. When F10 lands, every feature reads "Runs on a sample project" at best, and the guide says that the pilot (F11) is the first real use.
- **Style.** Short sentences and the second person, as in upstream's guide, in the voice of the `technical-writing` skill.

### 4.3 The merge permission

troy-mode merges its own PRs within its rights (R18). Claude Code's auto mode may still refuse `gh pr merge` as a merge without review, as it did once in troy-pstack. F07 then stops and names the permission to add (F07 section 8.6). `01-install.md` gives the line Troy adds to a project's `.claude/settings.local.json` before starting:

```json
{ "permissions": { "allow": ["Bash(gh pr merge *)"] } }
```

That file is git-ignored and Troy's own, so troy-init does not write it. The guide says that this lets troy-mode merge any PR in that project without a prompt, which its rights limit to the PRs that R18 allows.

### 4.4 The standing permission for trials

`09-changing-troy-mode.md` records the standing permission Troy added on 2026-11-08 as an `autoMode.allow` rule in troy-pstack's `.claude/settings.local.json` (F08 design section 11.3): nested `claude -p` sessions that load troy-pstack may create branches, issues, and PRs and merge PRs in `ZJUCao/troy-mode-trial` without asking. The page also says what it does not cover: any other repository, pushing `main`, and creating or deleting a repository. If a trial is refused anyway, the session tells Troy and does not work around it.

## 5. What F10 does not write

- **No second copy of the designs.** The guide explains what Troy types and sees, and links to the designs for how each step works inside.
- **No README in Chinese.** The README mixes Lauren's text, the port's notes, and troy-mode's section, and only troy-mode's documents follow R12. A Chinese README would translate upstream's text and drift with every upstream merge (D87). The README links to the Chinese guide.
- **No change to upstream's guide** or to `poteto-help`.

## 6. The plugin version (D89)

Claude Code installs a plugin from a marketplace as a copy, and updates the copy only when `version` in `.claude-plugin/plugin.json` rises. troy-pstack is still at 0.1.0, the version of the fork, and troy-init records that number in each project's `.troy-mode/install.toml` and in the title of an upgrade PR (F06 section 6). F10 raises it to **0.2.0**, the first version that documents troy-mode for use, and makes both descriptions name troy-mode:

- `plugin.json`: "Troy's Claude Code fork of Lauren Tan's pstack 0.15.36: verification-first engineering skills, principles, and subagent workflows, plus troy-mode, Troy's own workflow from requirements to released versions. Not affiliated with or endorsed by Lauren Tan or Cursor."
- `marketplace.json`: the same, without the last sentence, as now.

After F10 merges, Troy runs `claude plugin update troy-pstack@troy-pstack` and restarts Claude Code, as the README says, or installs the plugin for the first time. From then on, a troy-pstack PR that changes what projects get raises the version again: the patch number for a fix, the minor number for a feature. `09-changing-troy-mode.md` says so, and F11 relies on it to bring fixes into the pilot.

## 7. Changes to earlier features

- **troy-pstack's CI.** `troy-docs.yml` runs `python3 troy-mode/dev/check_links.py` after `check_pairs.py`. Its trigger already covers every Markdown file and `troy-mode/dev/**`.
- **F01 to F09** do not change. F10 reads their skills, engines, and designs, and the facts review (section 9.3) may find a mismatch between a design and what was built. Such a mismatch is fixed in the design or the code in its own PR, before F10's PR, and F10's PR description lists it.

## 8. How F10 maps to the requirements

| Requirement | Where F10 covers it |
| --- | --- |
| F10 row: a README section | Section 3 |
| F10 row: a usage guide in English and Chinese | Section 4 |
| F10 row: a note that troy-mode is Troy's own work | Section 3.2 |
| 3.1 and 3.2: the commands, and troy-mode or poteto-mode | Sections 3.1 and 4.1 |
| 3.3: where Troy takes part | `07-taking-part.md` |
| 5.1 to 5.10: every flow | `02-start.md` to `07-taking-part.md` |
| 7.1 and R13: status labels | Sections 4.2 and 9.5 |
| Section 8: no side effects on troy-pstack, and upstream merges stay easy | Sections 2 and 5 |
| Section 8: Language, the EN/ZH pairs | Sections 4.1 and 9 |
| Q10: one PR per feature | Section 1 |

## 9. How F10 is checked

### 9.1 The link check (D90)

`troy-mode/dev/check_links.py` uses Python 3.11 or newer and the standard library only, like `check_pairs.py`. It reads `README.md` and every Markdown file git tracks under `docs/troy-mode/`, and checks each link outside code blocks and inline code:

- A link to a file, relative to the linking file's folder, must name a file that git tracks. A link to a folder must name a tracked folder.
- An anchor, as in `../requirements.md#72-feature-list` or `#troy-mode`, must match a heading of the target Markdown file under GitHub's rules: lowercase, punctuation other than `-` and `_` removed, spaces turned into `-`, Chinese characters kept, and `-1`, `-2` added to repeated headings.
- Links with a scheme, such as `https:` or `mailto:`, are not checked, because CI should not depend on other sites.

It prints each broken link with its file and line. Exit codes are those of `check_pairs.py`: 0 when every link resolves, 1 when one does not, and 2 when the script cannot run.

### 9.2 Tests and planted bugs

A separate agent writes `test_check_links.py` from this design before the script exists, with `unittest` and a temporary git repository. Cases include: a missing file, an untracked file, a folder link, an anchor in the same file and in another file, Chinese headings, repeated headings, headings with punctuation and inline code, links inside a code block and inside inline code (ignored), reference-style links, and `https:` links (ignored).

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: anchors not checked, Chinese characters dropped from the anchor, repeated headings not numbered, links in code blocks checked, untracked files accepted, and links with a scheme checked. The counts go in the PR description.

### 9.3 Facts review

Before the PR opens, a fresh agent that did not write the guide reads it next to its sources: the skills `troy-mode` and `troy-init`, the engines' `--help` output, the agent files, F01's templates, the requirements, and the designs of F01 to F09. It lists every request, command, PR title, comment heading, path, config key, and status text in the guide that no source supports, or that a source contradicts. Each finding is fixed, or the PR description says why it stands.

### 9.4 Reader test

Two fresh agents each read only one language of the guide, with no other file, and answer these questions as Troy would need them answered:

1. How do I install troy-pstack, and how do I see that troy-mode is there?
2. How do I turn an empty folder into a troy-mode project?
3. My project already has code and tests. What happens to them?
4. What do I type to build the next feature, and where will troy-mode stop and wait for me?
5. How do I approve a design without opening GitHub?
6. After three features, troy-mode asks whether to keep approving designs. What does each answer do?
7. I found a bug in an accepted feature. What do I type, and which PRs follow?
8. I want an accepted feature to work differently. What happens to its tests?
9. How do I release v0.1, and what will troy-mode ask me to do on my own devices?
10. A scenario fails on my phone during the release. What do I reply, and what happens next?
11. How do I add a rule for this project when existing code breaks it?
12. How do I propose a rule for every troy-mode project?
13. troy-mode stopped with an escalation. What must my answer contain?
14. I closed the session in the middle of a feature. How do I continue in a new one?
15. A merge was refused by a permission. What do I do?
16. What is the difference between "Passes tests on main" and "Usable on Troy's devices"?
17. How do I make the Developer run on opus with high effort in one project?
18. How do I bring a newer troy-mode into an existing project?
19. Which parts of troy-pstack are Lauren Tan's work, and which are Troy's?

The build session grades each answer against the designs. A wrong or missing answer means the guide is fixed, and that question is asked again of a new agent. The PR description gives the result for each language.

### 9.5 Status

| When | F10's status in requirements 7.2 |
| --- | --- |
| The F10 PR merges | Written: the README section and the guide in English and Chinese, describing F01 to F09 as built. The pair and link checks pass, a facts review found no open mismatch, and a reader test answered all 19 questions from the guide alone in each language. Not yet followed on a real project. |
| The pilot (F11) ends, with the guide's fixes merged | Used on a real project: Troy followed the guide in the pilot of <project>, and the problems the pilot found in it are fixed. |

"Runs on a sample project" does not apply: the reader test reads the guide, but nothing in it runs. The status update is its own PR.

## 10. Not in F10

- Changing upstream's guide, `poteto-help`, or any upstream skill.
- A Chinese README (D87).
- Checking links to other sites.
- Documents for people other than Troy, such as a public install page (requirements section 9: one user).
- The pilot itself, and the guide fixes it finds (F11).

## 11. Decisions for Troy

F09's design ends at D85, so F10 continues from D86. Troy accepted every recommended answer on 2026-11-08.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D86 | Where does the guide live? | A: its own folder `docs/troy-mode/guide/`, about ten pages, each with a Chinese mirror, next to the requirements and designs (section 4). B: new pages in upstream's guide `docs/guide/`. C: one long page `docs/troy-mode/guide.md` and its mirror. | A. Upstream's guide is Lauren's work and English only, and changing it would mix authorship and make upstream merges harder (requirements section 8). C makes one very long page per language. |
| D87 | Is the README section bilingual? | A: English only, in `README.md`, with links to both languages of the guide (section 5). B: also a Chinese `README.zh-CN.md` of the whole README. | A. The rest of the README is upstream's and the port's text, which R12 does not cover, and a Chinese copy would drift with every upstream merge. The guide carries the Chinese. |
| D88 | How is troy-mode marked as Troy's own work? | A: the note of section 3.2 at the top of the README section and of the guide's first page, and troy-mode named as Troy's in `plugin.json` and `marketplace.json`. B: as A, plus a separate `NOTICE` file. | A. The note sits where a reader first meets troy-mode. The license is the same MIT License, so a `NOTICE` file adds nothing that `LICENSE` and the note do not say. |
| D89 | Does F10 raise the plugin version? | A: yes, to 0.2.0, and later troy-pstack PRs that change what projects get raise it again (section 6). B: no, it stays 0.1.0. C: to 1.0.0. | A. Without a new version, an installed troy-pstack never receives troy-mode, and every upgrade PR says 0.1.0. 1.0.0 should wait until the pilot has used it. |
| D90 | How are the docs checked? | A: the pair check, a new link check in CI (section 9.1), a facts review by a fresh agent, and a reader test in both languages (sections 9.3 and 9.4). B: as A, without the link check script: one agent checks the links once. C: as A, plus a walkthrough in nested `claude -p` sessions on `ZJUCao/troy-mode-trial` that follows the guide from setup to the first feature's PR 1, about $5 to $10. | A. The link check is small, uses the standard library, and keeps the guide's many links to designs and requirements from breaking later. C repeats what the trials and the pilot already do: the pilot follows the guide on a real project soon after. |
| D91 | When is F10 built? | A: after F09 merges, so the guide describes F08 and F09 as built, and before F11, so Troy uses the guide in the pilot. F10's row then depends on F08 and F09, and F11's row also depends on F10. B: now, in parallel with F09, from the F08 and F09 designs, with a follow-up PR when they land. C: after F11, so the guide includes the pilot's lessons. | A. The guide is checked against built code, and the pilot is its first real reader. B writes two of the flows twice. C leaves Troy without a guide during the pilot. This changes the dependency columns and the graph in requirements 7.2. |
| D92 | Does the guide cover work on troy-mode itself? | A: yes, one last page `09-changing-troy-mode.md`: the documents, the build process, the checks, trials and Troy's standing permission for them, who merges, and the plugin version (sections 4.1 and 4.4). B: no, the guide covers only using troy-mode. | A. Today these rules live only in the designs and in the agent's local memory. A page in the repository keeps them for any session and for Troy. |

Requirements 1.26 records the approved changes:

- The F10 row says what F10 builds (D86 to D90) and depends on F08 and F09 (D91).
- The F11 row also depends on F10, and the graph gets `F08 --> F10`, `F09 --> F10`, and `F10 --> F11` in place of `F07 --> F10` (D91).
- Section 8, Language: troy-pstack's CI also checks that the relative links and anchors in its troy-mode documents resolve (D90).

## 12. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-08 | First draft. |
| 1.0 | 2026-11-08 | Approved by Troy with D86 to D92, every recommended answer. |
