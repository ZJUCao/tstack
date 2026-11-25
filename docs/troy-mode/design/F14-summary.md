# F14 design: the summary for Troy

| | |
| --- | --- |
| Feature | F14 in [requirements 1.34](../requirements.md#72-feature-list) |
| Version | 1.2 |
| Date | 2026-11-25 |
| Status | Approved by Troy on 2026-11-14, with D131 to D137. Version 1.1 notes the changes of F20's design (D268 to D279, approved by Troy on 2026-11-22), which land with F20's build. Version 1.2 notes the changes of F18's design (D171 to D180, approved by Troy on 2026-11-25), which land with F18's build. |
| Source of truth | This English file. [`F14-summary.zh-CN.md`](F14-summary.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F14 gives Troy a short way into each PR that asks for Troy's approval. The PR's description opens with a one-page summary in Chinese and English: what changes for Troy as a user, each point Troy decides with a recommendation, and the risks, in everyday words (requirements 3.3, 5.2, and Q16).

F14 delivers:

1. the summary's three parts, its length limit, and its writing rules, as a new template (section 3, D133);
2. the PRs that get one (section 4, D132);
3. who writes it, and how it reaches the PR and the chat (section 5, D131 and D135);
4. a new Hard rule, R22, which troy-check checks in CI, and a seventh item in the Architect's design checklist (section 6, D134);
5. a new plugin version that brings it into the pilot (section 8, D137).

The summary lives in the PR description, not in a document. Designs, test plans, the requirements, and the architecture keep their shape, except one new row in the design's Architect review table. F14 lands in one PR (Q10).

## 2. What Troy reads today

In the pilot, `ZJUCao/recipe-menu`, Troy approves the design and the test plan of every feature: on 2026-11-11, after F03, Troy set `troy_approves_first = 16`. Each feature's two documents hold this much text, counted in characters:

| Feature | Design, English | Test plan, English | Both, English | Both, Chinese mirror |
| --- | --- | --- | --- | --- |
| F01 | 32,466 | 29,611 | 62,077 | 42,296 |
| F02 | 41,790 | 46,957 | 88,747 | 61,104 |
| F03 | 73,793 | 83,391 | 157,184 | 111,704 |
| F04 | 76,724 | 80,811 | 157,535 | 107,451 |
| F05 | 87,122 | 93,621 | 180,743 | 123,400 |
| F06 | 63,887 | 84,514 | 148,401 | 103,105 |
| F07 | 44,127 | 57,544 | 101,671 | 66,181 |
| F08 | 66,018 | 68,117 | 134,135 | 85,388 |
| F09 | 75,047 | 81,287 | 156,334 | 104,713 |
| F10 | 54,700 | 71,784 | 126,484 | 83,708 |

What tells Troy what to decide today is spread over three places, none of them written for Troy:

- **The PR description** follows the PR template: Why, What, Checks, and Soft-limit reason. In the pilot's 20 design and test plan PRs it holds 1,473 to 4,190 characters of English written for the record, with interface names, section numbers, and IDs. The template has no place for what Troy decides.
- **The design** names the points near the end of its section 2. F10's says "Troy decides these two points", points A and B, between paragraphs about modules and constants.
- **The comment `Waiting for Troy: approve this PR`** repeats the points in 185 to 1,065 characters, and the main session tells Troy in chat. They read as notes between roles: PR 59's points name the test case `F04-T38` and the constant `TO_TASTE`, PR 65's name the constant `EMPTY_WORD` and "the places `tag` and `名称`", and the architecture's PR 3 names ADR-0004 and PT01.

Troy has said that explanations full of jargon and IDs are hard to follow. F14 puts what Troy needs in one place, in a fixed shape, in plain words.

## 3. The summary

### 3.1 Where it goes

The summary is the first thing in the PR description, before Why. Its Chinese part comes first, then its English part (D135):

```text
## 给 Troy 的摘要          the Chinese part (section 3.2)
## Summary for Troy        the English part
## Why                     the PR template's sections, as today
## What
## Checks
## Soft-limit reason
```

The English part is the source, and the Chinese part says the same, as in every troy-mode document (R12). The Chinese part comes first because Troy talks with troy-mode in Chinese, and GitHub's notification e-mails and PR pages show the start of a description first.

When the PR waits for Troy, the main session also sends the summary in chat, in the language Troy writes in, with the PR's link (section 5.3).

### 3.2 Its parts

Each language has the same three parts, under fixed headings, in this order:

| English heading | Chinese heading | What it holds |
| --- | --- | --- |
| `### What changes for you` | `### 对你有什么变化` | What Troy will type, see, or do differently once the PR's content is built: new commands and options, changed output, new files Troy edits, and what stays the same. For a test plan: what the tests check of that, what they leave out, and anything Troy runs by hand. For the architecture: what Troy will notice, such as speed, the files the program keeps, tools to install, and what will be hard to change later. For the requirements: what the program will do, or do differently. |
| `### What you decide` | `### 需要你决定的事` | One numbered item for each point Troy decides, then the fixed reply line below. Each item: what is decided, in a few bold words; the options, as what Troy would see under each; `Recommended:` (`推荐：`) with the option and why, in one sentence. With nothing to decide, only `Nothing to decide.` (`没有需要你决定的事。`) and no reply line. |
| `### Risks` | `### 风险` | What could go wrong for Troy, how likely it is, and what happens then. `None found.` (`没有发现风险。`) when there is none. |

The reply line is the same in every summary:

- English: `Reply "all as recommended" (全按推荐) to take every recommendation, or give the number and the option you want.`
- Chinese: `回复「全按推荐」即可全部采用推荐，或写出编号和你选的方案。`

The summary repeats nothing from Why, What, or Checks. Those stay for the record and for the roles.

### 3.3 One page (D133)

"One page" is **at most 2,000 characters in each language**. A part is counted from the line after its `##` heading to the line before the next `##` heading, with blank space at both ends removed, as written, Markdown included. A character is one Unicode code point, so a Chinese character and a letter each count as one.

- 2,000 English characters are about 300 words, a minute or two of reading, and fit on one laptop screen.
- The Chinese part is shorter: next to a full English part it has about 900 to 1,200 characters, because Chinese takes about half as many characters as English. The example of section 3.5 has a ratio of 0.43, and troy-pstack's own pairs have 0.51 (F11 design), 0.52 (F10 design), and 0.59 (guide page 03). Inline code, such as a command, keeps its length in both.
- Today's `Waiting for Troy` comments, at 185 to 1,065 characters, would fit, and so does the example of section 3.5 with two points. The summary of this design's own PR, with seven points, fits with 1,977 English characters: its first draft had 2,033 and lost one sentence. A design with more points must say each one more shortly or be split, and that is the purpose of the limit.

A project can change the limit in `.troy-mode/config.toml`, as `[summary] max_chars`, through the rule change flow, as with any troy-check limit (F09 design D84).

### 3.4 Plain words (D133)

The template's guidance and the authors' instructions give these rules:

1. **Write for Troy as a user.** Say what Troy types, sees, or must do. Do not say how the code is built.
2. **No internal IDs.** No rule IDs (R03, P01), decision IDs (D12), question IDs (Q4), test case IDs (F04-T07), scenario IDs (v0.1-S03), ADR numbers, performance target IDs (PT01), task IDs (IF1), or section numbers. Name the thing instead: "the 1-second limit for search", not "PT01". Feature IDs such as F10, bug numbers such as #12, and version numbers such as v0.1 may appear, because Troy sees them in PR titles and in the status table.
3. **Code only for what Troy types or sees**, in backticks: commands, options, file names Troy edits, and the program's output. No function, module, class, or constant names.
4. **Short sentences in everyday words.** Explain in a few words any term Troy might not know, or leave it out.
5. **Every option says what Troy would see under it.** "An error that asks for a word", not "raises `UsageError`".
6. **Every recommendation says why, in one sentence.**

### 3.5 An example

The F10 design's summary, written by these rules from the approved design. It has 491 Chinese and 1,137 English characters.

```markdown
## 给 Troy 的摘要

### 对你有什么变化

你可以输入 `recipe-menu search 词...` 来找菜谱。它列出名称、食材或标签里包含你给的每一个词的菜谱，中英文都行，英文不分大小写，每一行还写明词是在哪里找到的。帮助里多一行 `search`。别的命令都不变。

### 需要你决定的事

1. **原型里没有的新提示。** 例如 `2 recipes match "葱" and "quick".` 和 `没有菜谱匹配“lamb”。`。推荐：照写的接受，它们和原型里的句子是同一种说法。
2. **输入空词，比如 `search ""`。** 方案 1：报错，提示你写一个词。方案 2：当作什么都没找到。推荐：方案 1，因为打错字不该看起来像“没有这个菜”。

回复「全按推荐」即可全部采用推荐，或写出编号和你选的方案。

### 风险

- 速度：1,000 个菜谱时，`search` 在你的电脑上大约要 0.8 秒，离 1 秒的上限不远。以后哪次改动让它变慢，会先单独提速。
- `search` 不查菜谱的编号，所以拼错的编号，比如 `tomato-eggs`，什么也找不到。

## Summary for Troy

### What changes for you

You can type `recipe-menu search WORD...` to find recipes. It lists the recipes whose name, ingredients, or tags hold every word you give, in English or Chinese, with English capitals ignored, and each row says where the word was found. The help gains a line for `search`. No other command changes.

### What you decide

1. **New messages that no prototype shows.** For example `2 recipes match "葱" and "quick".` and `没有菜谱匹配“lamb”。`. Recommended: accept them as written, because they follow the prototype's sentences.
2. **An empty word, such as `search ""`.** Option 1: an error that asks you for a word. Option 2: it finds nothing. Recommended: option 1, because a typing mistake should not look like "no such recipe".

Reply "all as recommended" (全按推荐) to take every recommendation, or give the number and the option you want.

### Risks

- Speed: with 1,000 recipes, `search` takes about 0.8 seconds on your PC, close to its 1-second limit. If a later change slows it down, a speed fix comes first, in its own PR.
- `search` does not look at recipe IDs, so a mistyped ID such as `tomato-eggs` finds nothing.
```

The description of this design's own PR opens with a summary in the same shape, as a second example.

## 4. Which PRs get one (D132)

| PR | Title | Who writes its document | Gets a summary |
| --- | --- | --- | --- |
| Interface design (PR 1) | `[F04 1/6 design] <name>` | Interface Designer | Yes (requirements 5.2) |
| Test plan (PR 2) | `[F04 2/6 test-plan] <name>` | Test Manager | Yes |
| Requirements | `[docs] Add the requirements`, `[docs] Change the requirements: <summary>` | Product Manager | Yes |
| Architecture | `[docs] Add the architecture`, `[docs] Change the architecture for <ID>` | Architect | Yes |
| Release | `[docs] Release <tag>` | Product Manager | No. F08's message to Troy already lists the scenarios Troy runs on Troy's devices (F08 design 5.6). |
| Every other PR | | | No. Troy does not approve them. |

These are the PRs whose document Troy approves (requirements 3.3, steps 1 to 3). A design or test plan PR gets its summary even when troy-mode merges it, after the first `troy_approves_first` features, for three reasons:

- R22 can then tell from the title alone whether a PR needs one, with no knowledge of the merge rights (section 6.1).
- Once approvals become spot checks (F18), Troy reviews a sample of these PRs, and the summary is how Troy reads one quickly.
- A summary costs the author about 3,000 characters of writing, against 60,000 to 180,000 for the documents.

An escalation is not a PR and keeps its own shape (Prototype C, requirements 5.7).

## 5. Who writes it (D131)

### 5.1 The authors

The role that writes the document writes its summary, because it knows the document best:

| Document | Author | Tasks that return a summary |
| --- | --- | --- |
| Interface design | Interface Designer | IF1, and IF2 for each revision |
| Test plan | Test Manager | TM1, and each run of TM1 again after a question or a ruling |
| Architecture | Architect | AR1, and the run that writes an architecture change |
| Requirements | Product Manager, in the main session | PM1 and PM2 |

The main session runs the Product Manager, so it writes the requirements' summary itself. For every other document it reads the summary but does not write it. Writing it would mean reading a document of 60,000 to 180,000 characters in the main session, whose context the pilot already compacted 10 times.

### 5.2 The report field

The reports of the Interface Designer, the Test Manager, and the Architect gain a last field:

```text
For Troy: <None, or the filled summary template. It runs to the end of the report.>
```

It holds the filled template `troy-mode/templates/summary-for-troy.md` (section 7) in the tasks of section 5.1, and `None` in every other task. The brief of each of those tasks says so: the engine's task sentences for IF1, IF2, TM1, AR1, and AR6's architecture change add "Write the summary for Troy from the summary-for-troy template in your report's For Troy field." When AR4 writes an architecture change in the requirement change flow, the main session adds the same sentence to the brief's Input.

### 5.3 From the report to the PR and the chat

The main session:

1. **Writes the description**: the report's For Troy block first, unchanged, then Why, What, Checks, and Soft-limit reason, as today.
2. **Reads the summary once** against section 3.4. It may reword a sentence to make it plainer, but it never changes what a point, an option, or a recommendation says. A change of meaning goes back to the author as a round.
3. **Runs the local checks.** `troy-check pr --body-file` now runs R22 too. A failure goes back to the author as Input and counts as an attempt, as every failing check does (F07 design D64). A report with no For Troy block is such a failure.
4. **Gives AR2 the summary**, in the Input of its brief, for the checklist's seventh item (section 6.2).
5. **After each revision** replaces the summary in the description with the new one, with `gh pr edit <number> --body-file <file>`. CI runs again on the edit.
6. **When the PR waits for Troy**, posts `Waiting for Troy: approve this PR` with one line under it: "What to decide is in the summary at the top of the description." Then it sends Troy the summary in chat, in the language Troy writes in, as the description has it, with the PR's link.

The requirements' summary is written by the main session as the Product Manager, in step 1, and goes through steps 2, 3, and 6.

### 5.4 Troy's reply

The reply works as today (F07 design D61):

- "全按推荐", "all as recommended", or "approved" approves the PR with every recommendation. troy-mode records the approval, and the description's What says that Troy took every recommendation.
- A reply that picks another option, such as "2: option 2", asks for changes. The author revises, as a round, and the PR waits for Troy again. Whether such a PR needs Troy again after the revision is F18's question, not F14's.

## 6. How it is checked (D134)

### 6.1 R22 in troy-check

A new Hard rule:

> **R22.** The description of every design, test plan, requirements, and architecture PR opens with a summary for Troy, in Chinese and English: what changes for Troy, each point Troy decides with a recommendation, and the risks. Each language has at most 2,000 characters and holds no internal IDs.

`troy-mode/checks/troycheck/summary.py` checks it as part of `troy-check pr`, so it runs in the local checks and in CI. In CI the checker runs from the base commit, as every PR check does (F02 design 8), so R22 starts with the first PR opened after the upgrade that brings it has merged.

**Which PRs.** R22 applies when the title's kind is `design` or `test-plan`, or when it is `docs` and its summary starts with `Add the requirements`, `Change the requirements`, `Add the architecture`, or `Change the architecture`. For every other PR it reports SKIP, "Not a PR that needs a summary." Without a description, as in a local run without `--body-file`, it reports SKIP too. CI always passes the description.

**What it checks.** Each check that fails adds one line to R22's FAIL:

| Check | Fails when |
| --- | --- |
| Order | The first line that is not blank is not `## 给 Troy 的摘要`, or the next `##` heading is not `## Summary for Troy`. |
| Parts | A part does not have exactly the three `###` headings of section 3.2, in that order, each with text under it. |
| Length | A part has more than `max_chars` characters, counted as section 3.3 says. The message gives the count and the limit. |
| Decisions | Under the decide heading, a numbered item (a line that starts with `1.`, `2.`, and so on, not indented) has no `Recommended:` in English or no `推荐：` or `推荐:` in Chinese; or there is no numbered item and the text is not `Nothing to decide.` or `没有需要你决定的事。`; or the two parts have different numbers of items. |
| Chinese | A `###` part of the Chinese summary holds no Chinese character. |
| IDs | Either part holds an internal ID outside inline code and code blocks (table below). The message names the ID and its line. |

| Internal ID | Pattern | Example |
| --- | --- | --- |
| Rule | `R` or `P` and two digits | R03, P01 |
| Decision | `D` and one to three digits | D61 |
| Open question | `Q` and one or two digits | Q16 |
| Test case | `F` or `B`, digits, `-T`, digits | F04-T38 |
| Scenario | `v`, a version, `-S`, digits | v0.1-S23 |
| ADR | `ADR-` and digits | ADR-0004 |
| Performance target | `PT` and digits | PT01 |
| Role task | `AR`, `IF`, `TM`, `DV`, `TE`, `CR`, or `PM`, and one digit | IF1 |

An ID matches only when no ASCII letter or digit stands right before or after it, so `F10` and `3D` do not match, and an ID right after a Chinese character, as in `见R03`, does. IDs in inline code are left to the authors and the main session, because commands and program output go there.

**Config.** `config.default.toml` gains `[summary] max_chars = 2000`, read from the merge-base commit like every limit.

R22's checks are about shape. R20 keeps checking that no template marker or guidance comment is left, and R19 that the description carries no attribution.

### 6.2 The Architect's seventh item

The Architect's interface checklist (requirements 5.2, AR2) gains a seventh item:

- **The summary for Troy says what the design says, and lists every point Troy decides.**

The design template's section 4 table gains its row, in both languages, and AR2 fills it from the summary in its Input. A point the Architect finds for Troy, such as the non-blocking findings that PR 59 offered Troy as a choice, is a finding under this item: the Interface Designer adds it to the design and to the summary in the next round, so every point Troy decides is in the summary.

### 6.3 What no check covers

- Whether the words are plain enough. R22 catches IDs and the shape, the main session reads each summary (section 5.3, step 2), and Troy's remarks during the pilot show the rest.
- Whether the summary of a test plan, the requirements, or the architecture matches its document. No role reviews those documents before Troy, so only the main session reads their summaries. The dry run of section 9.3 compares summaries with their documents once.

## 7. Location and changes to earlier features

```text
troy-mode/
  templates/
    summary-for-troy.md            new: the summary's skeleton and guidance (section 3)
    pull-request.md                its guidance names the summary
    feature-design.md, .zh-CN.md   section 4 gains the seventh row
    rules.md, .zh-CN.md            the R22 row
    README.md, .zh-CN.md           list the new template
  checks/
    troycheck/summary.py           new: R22 (section 6.1)
    troycheck/cli.py, config.py    run R22, read [summary]
    config.default.toml            [summary] max_chars = 2000
    tests/test_r22.py              new: R22's tests
  flow/
    troyflow/brief.py              the task sentences of IF1, IF2, TM1, and AR1
    troyflow/rulebrief.py          the task sentence of AR6's architecture change
    tests/                         the brief tests for those sentences
  roles/product-manager.md         PM1 and PM2 write the requirements' summary
agents/
  troy-interface-designer.md       IF1, IF2, and the For Troy report field
  troy-test-manager.md             TM1 and the For Troy report field
  troy-architect.md                AR1, AR2's seventh item, and the For Troy report field
skills/troy-mode/SKILL.md          the PR description, the chat message, and the Waiting comment
docs/troy-mode/guide/              pages 02, 03, 07, and 08, in both languages
.claude-plugin/plugin.json         the next minor version (section 8)
```

| Feature | Change |
| --- | --- |
| F01 Templates | The new template `summary-for-troy.md`. It is one file, like `pull-request.md`, because both languages go into one description. Its guidance comment gives the rules of sections 3.2 to 3.4. `pull-request.md`'s guidance says that a design, test plan, requirements, or architecture PR starts with the author's summary. `feature-design.md` and its mirror gain the seventh row of section 4. `rules.md` and its mirror gain R22. |
| F02 Checks | R22 (section 6.1) and its config key. `PR_CHECKS` gains it after R20. |
| F04 Roles | The Interface Designer, the Test Manager, and the Architect write the summary in the tasks of section 5.1 and report it in For Troy. AR2 checks the seventh item. The Product Manager writes the requirements' summary in PM1 and PM2. |
| F06 troy-init | Nothing in its code. It copies `troy-mode/templates/` whole, so setup and upgrade bring the new template, and upgrade replaces the R rows of `docs/rules.md` with the template's, which adds R22 (F06 design 6). |
| F07 Entry skill | Section 5.3's steps, in "One stage" step 5, in "Troy's approval", in project setup, and in the requirement change flow. The requirement change flow's architecture PR gets the title `[docs] Change the architecture for <ID>`, as the rule change flow's has, so R22 finds it. The engine's task sentences of section 5.2. |
| F10 Guide | `02-start.md`: the summary on the requirements and architecture PRs. `03-features.md`: what Troy sees at PR 1 and PR 2. `07-taking-part.md`: how to reply. `08-reference.md`: R22 and `[summary] max_chars`. Each in both languages. |

No upstream pstack file changes.

## 8. How the pilot gets F14 (D137)

F14's build PR in troy-pstack raises the plugin's version. F14 is a feature, so it raises the minor number (F10 design D89), and it takes the next free one when it merges: 0.3.0 if neither F12 nor F13 has raised it first. A patch number is for a fix of a blocker (F11 design D96).

Then, with no pause in the pilot:

1. **Troy updates the plugin** with `claude plugin update troy-pstack@troy-pstack` and restarts Claude Code (F10 design 6). When F12 or F13 lands the same day, one update and one restart bring all of them, so the coordinating session tells Troy once, after the last of them merges.
2. **Troy types `/troy-pstack:troy-mode upgrade troy-mode`** in the pilot folder. troy-init's `[rules] Upgrade troy-mode to <version>` PR replaces troy-check, which now has R22, the templates, the PR template, and the R rows of the rules table, and troy-init merges it when its checks pass (F06 design 6, F11 design 7). The skill, the agents, and the engine come with the plugin itself.
3. **The next design or test plan PR** opens with a summary. troy-mode works on one PR at a time, so the upgrade waits until an open stage PR has merged, and no PR is checked by R22 halfway through.

The pilot is at F10's implementation now, with F11, F12, and F13 still to come. Each design and test plan PR after the upgrade has a summary, and the pilot report says which ones did (F11 design 8).

## 9. How F14 is checked (D136)

### 9.1 Tests

A separate agent writes the tests from this design, before the code exists, with `unittest` and a temporary git repository, as for F02's checks. `test_r22.py` covers at least:

- each PR kind of section 6.1, with and without a summary, and a `[docs]` PR of another kind, which is skipped;
- a summary that passes, in the shape of section 3.5;
- each line of section 6.1's table failing on its own: the wrong order, a missing or renamed part, a part with no text, 2,001 characters in one language, an item with no recommendation, unequal numbers of items, the nothing-to-decide text, a Chinese part with no Chinese character, and each kind of ID;
- an ID in inline code and in a code block (passes), right after a Chinese character (fails), and inside a longer word such as `F10` or `PR03X` (passes);
- `max_chars` from the merge-base commit's config, so a PR cannot raise its own limit;
- CRLF line endings in the description.

The brief tests check the new task sentences. The suites of checks, init, flow, dev, and hooks pass on Linux and Windows.

### 9.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail: the length counted in bytes, the limit read from the PR's own commit, the order of the two parts not checked, the count of items not compared, IDs searched inside inline code, `\b` used at an ID's edge so that `见R03` passes, and the `docs` prefixes not matched. The counts go in the build PR's description.

### 9.3 A dry run on the pilot's documents

In the build session, fresh agents follow the new instructions of IF1 and TM1 on the pilot's approved F09 and F10 designs and test plans, read from `D:\Troy\Projects\recipe-menu` and written nowhere there. R22's code checks the four summaries. Another fresh agent reads each summary next to its document and lists what it gets wrong or leaves out. The build PR's description shows the four summaries and the findings, so Troy sees what F14 writes before the pilot gets it.

### 9.4 Status

| When | F14's status in requirements 7.2 |
| --- | --- |
| The build PR merges | Written: R22 passes its tests, and summaries that the new instructions wrote for the pilot's F09 and F10 designs and test plans pass R22. Not yet used on a real project. |
| Troy approves a design or test plan PR of the pilot from its summary | Used on a real project: the design and test plan PRs of <features> of `ZJUCao/recipe-menu` opened with a summary, and Troy approved them from it. |

The status updates are their own PRs.

## 10. How F14 maps to the requirements

| Requirement | Where F14 covers it |
| --- | --- |
| F14 row: each interface design PR opens with a one-page summary | Sections 3 and 5 |
| F14 row and Q16: whether other PRs that wait on Troy get one | Section 4 |
| Q16: in English and Chinese | Section 3.1 |
| 3.3: where Troy takes part | Sections 4 and 5.3 |
| 5.2: PR 1's description, and the Architect's checklist | Sections 3.1 and 6.2 |
| Section 6: Hard rules enforced by CI | Section 6.1 |
| Section 8: Language | Section 3.1 |
| Q10: one PR per feature | Section 1 |

## 11. Not in F14

- Summaries for escalations, release PRs, and the other PRs of section 4.
- Changing the documents themselves, or making them shorter.
- Whether a PR waits for Troy again after a revision that applies Troy's own choice (F18).
- Progress issues on GitHub (F15).
- Checking how plain the words are beyond IDs and shape (section 6.3).

## 12. Decisions for Troy

F12 and F13 use D101 to D130, so F14 starts at D131. Troy accepted every recommended answer on 2026-11-14.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D131 | Who writes the summary? | A: the role that writes the document, in its report: the Interface Designer for a design, the Test Manager for a test plan, the Architect for the architecture, and the Product Manager for the requirements. The main session puts it into the PR and the chat (section 5). B: the main session writes every summary from the document. C: a new first section of each document, which the main session copies into the PR. | A. The author knows the document best. B makes the main session read 60,000 to 180,000 characters per feature, in a context that the pilot already compacted 10 times. C makes every document longer, keeps a list of open decisions in it after Troy has decided them, and does not fit a change to the requirements or the architecture, whose summary is about the change, not the whole document. |
| D132 | Which PRs get one? | A: every design, test plan, requirements, and architecture PR, whoever merges it (section 4). B: design PRs only, as requirements 5.2 says now. C: all four, but only while Troy approves them. | A. Troy approves all four kinds. A rule keyed by the title stays simple, and once approvals become spot checks (F18), the summary is how Troy reads a sampled PR. |
| D133 | What are "one page" and "plain words"? | A: at most 2,000 characters in each language, about 300 English words; the three parts of section 3.2; and the writing rules of section 3.4, with no internal IDs. B: at most 40 lines in each language. C: no fixed limit; the main session judges. | A. A count of characters is easy to check and to explain. 2,000 is almost twice today's longest `Waiting for Troy` comment, and this design's own summary, with seven points, fits. Lines vary with screen width. C depends on Claude remembering, which troy-mode avoids. |
| D134 | How is it checked? | A: a new Hard rule R22 in troy-check, run in CI (section 6.1), and a seventh item in the Architect's design checklist (section 6.2). B: the same check as a Soft rule, which a PR passes with a written reason. C: no check; the main session reads each summary. | A. troy-mode enforces its rules with checks, not memory (requirements 1). A missing or overlong summary is never right, so a reason should not let it through. The Architect already reads the whole design, so it is the one who can say that the summary matches it. |
| D135 | In which order, and what does Troy get in chat? | A: the Chinese part first, then the English part, at the top of the description. In chat, the summary in the language Troy writes in, with the link. The `Waiting for Troy` comment shrinks to one line that points to the summary (section 5.3). B: English first, then Chinese. C: English in the PR only, Chinese in chat only. | A. Troy talks with troy-mode in Chinese, and GitHub shows the start of a description first. The English part stays the source, as for documents. C leaves the PR, which Troy may read on a phone, without Chinese. |
| D136 | How is F14 checked before the pilot gets it? | A: tests written from this design by a separate agent, planted bugs, and a dry run on the pilot's F09 and F10 designs and test plans, shown to Troy in the build PR (section 9). B: A, plus a trial on `ZJUCao/troy-mode-trial` that runs one feature's design and test plan PRs in nested sessions, about $5 to $10. C: tests only. | A. The dry run shows real summaries of real documents for little cost, and the pilot's next design PR is a real run soon after. B adds hours before the pilot gets F14. C shows Troy nothing before the pilot. |
| D137 | How and when does the pilot get F14? | A: the build PR raises the plugin's minor version; Troy updates the plugin and restarts once, together with F12 and F13 when they land the same day, then types "upgrade troy-mode" in the pilot; the pilot does not wait (section 8). B: the pilot pauses before its next design PR until F14 is in. C: after the pilot's v0.1 release. | A. F14 does not block the pilot, so a pause costs Troy time for nothing, and one restart for several features saves Troy interruptions. C would test F14 on no real PR before v0.1. |

Requirements 1.34 records the approved changes:

- The F14 row says what F14 builds (D131 to D137).
- 3.3: every design, test plan, requirements, and architecture PR opens with the summary, Chinese first (D132, D135).
- 5.2: PR 2's description also opens with the summary, and the Architect's interface checklist gains its seventh item (D132, D134).
- Section 6: the new row R22, Hard, enforced by CI (D134).
- Q16: answered by D132 and D135.

## 13. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-14 | First draft. |
| 1.0 | 2026-11-14 | Approved by Troy with D131 to D137, every recommended answer. |
| 1.1 | 2026-11-22 | F20's design (D268 to D279, approved by Troy on 2026-11-22): when several PRs wait for Troy, the skill asks about all of them in one message, each with its summary; the summaries themselves do not change (sections 5.3 and 5.4). The change lands with F20's build. |
| 1.2 | 2026-11-25 | F18's design (D171 to D180, approved by Troy on 2026-11-25): a spot-checked PR's summary for Troy is what Troy reviews after the merge, and a ruling at round 3 gets one line in the report to Troy; the summaries themselves do not change (sections 5.3 and 5.4; F18 design sections 5.3 and 7.1). The changes land with F18's build. |
