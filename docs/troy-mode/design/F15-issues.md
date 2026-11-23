# F15 design: issues for Troy

| | |
| --- | --- |
| Feature | F15 in [requirements 1.39](../requirements.md#72-feature-list) |
| Version | 1.3 |
| Date | 2026-11-23 |
| Status | Approved by Troy on 2026-11-16, with D141 to D150. Version 1.1 records the facts the build and its trial settled. Version 1.2 notes the changes of F20's design (D268 to D279, approved by Troy on 2026-11-22), which land with F20's build. Version 1.3 follows F07's D284 to D287 for tstack issue #67, approved under Troy's standing yes of 2026-11-22: notes for later features are troy-mode's comments on progress issues (sections 3.3, 4.2, 4.4, and 8.4). |
| Source of truth | This English file. [`F15-issues.zh-CN.md`](F15-issues.zh-CN.md) is the Chinese mirror. |

## 1. Scope

F15 lets Troy follow and steer a troy-mode project from a phone, through GitHub issues in the project's repository (requirements 3.3, 5.4, and 5.5). It delivers three kinds of issue:

1. **A progress issue for each feature**, with its six PRs as a checklist, kept up to date at every step and closed at acceptance (section 4, D142).
2. **Idea issues.** Troy opens one for each new idea or change request, and the Product Manager turns it into a requirement change, or a bug, a rule, or an answer (section 5, D143).
3. **A device-test checklist for each version**, with the scenarios Troy runs on Troy's devices. Troy ticks them while testing and accepts the version with the last box (section 6, D144).

Around them, F15 settles:

- who writes each issue and when: a new engine command renders the issues from the state, and the main session posts them (section 3, D141);
- how Troy's phone edits and comments come back, on issues and on PRs that wait for Troy (section 7, D145);
- the labels, the language, and what an issue holds or only links to (section 8, D146);
- what happens when `gh` or the network fails (section 9, D147);
- the checks and hooks (section 10, D148);
- how existing projects get F15, and the plugin version (section 12, D149);
- how F15 is checked before a real project gets it (section 13, D150).

Documents stay in the repository. The checks and the hooks read them as files, and 12 of the pilot's 44 English documents are longer than GitHub's limit for an issue body. An issue is a view of the state, like the progress file (F07 D58), or an input from Troy. F15 lands in one PR (Q10).

## 2. What the pilot and two probes showed

- **No issue yet.** On `ZJUCao/recipe-menu`, troy-mode merged 98 PRs and opened no issue. Troy followed the work in chat and on the release PR. At the v0.1.0 release, Troy ran three scenarios on Troy's devices, a PC install, Chinese text in Windows Terminal, and the shopping list on the phone, and replied "All accepted" in chat. The scenarios' steps are rows of a Markdown table in the version test plan, which a phone shows as a wide table.
- **The body limit is in characters.** A probe on `ZJUCao/troy-mode-trial` on 2026-11-16 tried to create an issue whose body held 65,537 characters, almost all Chinese (196,563 bytes). GitHub refused it: "Body is too long (maximum is 65536 characters)". No issue was created. Comments have the same limit.
- **Labels come first.** A second probe ran `gh issue create --label` with a label the repository lacked. `gh` refused it, "could not add label: 'f15-probe-missing-label' not found", and created nothing. So the labels of section 8.1 must exist before the first issue that uses them.
- **No notification.** Every role acts through Troy's account (F04 D29), so every issue, comment, and edit that troy-mode makes is Troy's own on GitHub. GitHub never notifies a person about their own activity. Troy sees the issues by opening them, and troy-mode still tells Troy in chat what waits (section 7).
- **Text reaches GitHub unchecked.** A review comment on `ZJUCao/recipe-menu#92` was posted although `check-text` had failed on it: the command read the check's output instead of its exit code. F05's `gh` guard checks only `gh pr create` and `gh pr edit` (F05 design 8.2), so issue bodies and comments pass unchecked today. troy-pstack's issue #65, which Troy approved on 2026-11-16, widens the guard (section 10).
- **The trial repository.** In `ZJUCao/troy-mode-trial`, v0.1.0 is released, and v0.2 holds F04 "Word count command", accepted, and F02 "Count lines", whose design has merged (PR #29). Its v0.2 test plan has 17 scenarios, all automated, so no scenario needs Troy's devices yet.

## 3. Who writes the issues (D141)

### 3.1 The rule

The engine works out what each issue should say, and the main session posts it. This keeps F07's line: the engine reads git and GitHub and never writes to GitHub, and the skill does every write (F07 design 3.1, F04 D29). Every post then runs through `check-text` and F05's `gh` guard, which see the main session's tool calls but not a program's own subprocesses.

| Issue | Created by | When | Changed by | Closed |
| --- | --- | --- | --- | --- |
| Progress | The main session, from the engine's `issues` report | When the feature becomes the next feature, or gets a stage PR (section 4.1) | The same, at every sync | By PR 6's `Closes #<n>` at acceptance, and by the sync |
| Idea | Troy, on the phone or the web. Also the main session, for an idea Troy gives in chat that troy-mode does not act on now (section 5.5). | Any time | Troy. troy-mode only comments and labels. | By the PR that acts on it, such as a requirement change's `Closes #<n>`, or by the main session after an answer (section 5.4) |
| Device-test checklist | The main session, from the engine's `issues` report | After a release test passes (section 6.1) | Troy ticks the boxes. The sync changes the text only when a new release test run starts. | By the sync, once the release PR has merged |

A bug keeps its own issue from the bug flow (F07 design 11.1): PR A mentions it and PR B fixes it, so its timeline already shows its progress.

### 3.2 The engine command `issues`

```text
python troy_flow.py issues [--device-test-scenarios <ID>,<ID>...] [common options]
```

`issues` reads the state as `status` does, plus the repository's labels and its issues, and compares what each progress and checklist issue should be with what it is. It changes nothing. Its report lists:

| Field | What it holds |
| --- | --- |
| `labels` | Each label of section 8.1 that the repository lacks, with the `gh label create` command that makes it. |
| `actions` | Each change, in order: `create`, `edit`, `close`, `reopen`, or `close-duplicate`, with the issue's kind, item (`F04` or `v0.1.0`), number, title, and labels, the body file it wrote under `<git dir>/troy-mode/flow/issues/`, and the exact `gh` command. |
| `skipped` | What it left out and why, such as a repository with issues turned off. |
| `problems` | A body it had to shorten (section 8.3). |

- A body is rebuilt from the state each time, so a sync that failed or never ran is repaired by the next one.
- `edit` appears only when the title or body differs from the rebuilt one. For a checklist, Troy's ticks are read first and kept, so ticking alone never causes an edit (section 6.3).
- `--device-test-scenarios` names the scenarios of a patch release's checklist when the main session creates it, because which scenarios a fix touched is a judgment (F08 design 6). The checklist's own text keeps that list for later syncs.
- Exit codes are F07's: 0 when it could read the state, 2 when it could not.

### 3.3 What `status` adds

`status` gains an `issues` part and one new action. It reads the issues with at most two more `gh` calls: every issue, open and closed, with its comments, and every PR, open, merged, and closed, for the stage PR numbers that `issues.pending` needs. The build chose these two reads over the open issues and the progress issues in every state: one list then serves the ideas, the progress issues, and the checklists.

- `issues.ideas`: each open idea issue (section 5.1), with its comments, and `new` when troy-mode has not answered it or Troy has written since troy-mode's last comment.
- `issues.troy_comments`: Troy's comments on progress and checklist issues since troy-mode's last comment on each. A `Note for <ID>` comment (section 8.4) does not count as troy-mode's last comment, so a note never hides a comment of Troy's that waits for an answer.
- `issues.device_test`: the open checklist's tag, run, the scenarios with their ticks, the accept box, and `result`: `waiting`, `ticked` (every scenario and the accept box ticked), or `incomplete` (the accept box ticked while a scenario is not).
- `issues.pending`: how many changes `issues` would make.
- `next.issue`: the feature's progress issue number, on a `stage` or `continue-pr` entry.
- **The `ideas` action** (section 5.2).
- PR comments: the engine also reads the bodies of Troy's PR reviews, because GitHub's "Comment" review is how a phone reply on a PR may arrive (section 7).

### 3.4 What the skill does

1. **Start.** After `status`, run `issues --json` and apply it, before routing. So a phone edit that changed troy-mode's text is repaired, and the labels exist before Troy opens an idea.
2. **After every step.** Right after each `status --write-progress` (F07 design 8.2, step 8), run `issues --json` and apply it.
3. **Apply.** Run each `labels` command. For each action, check the body file with `troy_flow.py check-text --file <file>` and read its exit code, never its output, then run the action's command.
4. **When something fails,** follow section 9: note it and go on.

## 4. The progress issue (D142)

### 4.1 Which features have one

A feature has an open progress issue while it is not accepted and either it is the next feature in the order (F07 design 5.1) or it has a stage PR, open or merged. The sync creates it, so the next feature's issue appears as soon as the feature before it is accepted, with nothing ticked.

- When the feature is accepted, its issue closes (section 4.5).
- When a feature with no stage PR stops being the next one, for example after a requirement change reorders the features, the sync closes its issue as "not planned", and reopens it when the feature is next again.
- A feature that leaves the requirements gets the same.
- An accepted feature never gets a new one. A change to it becomes a new feature (F07 D65), which gets its own issue.

### 4.2 What it shows

The title is the feature's ID and name, Chinese first: `F04 把历史导出为 CSV / Export history as CSV`, or `F04 Export history as CSV` when the mirror gives the same name. The body, for a feature at stage 3:

```markdown
<!-- troy-mode: progress F04 -->
**F04 把历史导出为 CSV** · v0.2 · 第 3 步，共 6 步

等你：没有。

- [x] 1/6 接口设计：#41，已合并
- [x] 2/6 测试计划：#42，已合并
- [ ] 3/6 模拟：#43，进行中。代码审查员第 1 轮：要求修改
- [ ] 4/6 测试
- [ ] 5/6 实现
- [ ] 6/6 验收

依赖：F02（#7，已验收），F03（#9，已验收）
文档：需求 · 设计 · 测试计划 · 原型（链接）

troy-mode 维护这段文字，改动会被替换。想对 troy-mode 说什么，请写评论。

<details><summary>English</summary>

**F04 Export history as CSV** · v0.2 · stage 3 of 6

Waiting for you: nothing.

1/6 Interface design: #41, merged
2/6 Test plan: #42, merged
3/6 Mock: #43, open. Code Reviewer, round 1: changes requested
4/6 Tests
5/6 Implementation
6/6 Acceptance

Depends on: F02 (#7, accepted), F03 (#9, accepted)
Documents: requirements · design · test plan · prototype (links)

troy-mode keeps this text and replaces edits to it. To reach troy-mode, write a comment.

</details>
```

- **The boxes** are troy-mode's: a stage is ticked when its PR has merged. A mock that the requirement change flow skips (F07 D65) is ticked with "skipped: no new interface".
- **The stage line** names the stage's PR and its state. For the open PR, it adds the last review or attempt heading, translated into fixed words, such as "Code Reviewer, round 1: changes requested".
- **"Waiting for you"** says what waits on Troy, from `status`: "approve #41; what to decide is at the top of its description", or an escalation with its link.
- **The status** is the feature's Status cell in the requirements and its mirror, shown when it says more than "Not started": "Needs rework (<the change>)" during a rework, and the new status at acceptance.
- **Other lines,** when they exist: side PRs whose title names the feature, such as `[F04 test-fix]`; bug issues titled `Real run of F04: ...` (F12 design D107); a stage PR closed unmerged; "Needs rework" with the change that caused it; and the notes that earlier work left for the feature, "备注：2 条（#31、#40）" and "Notes from earlier work: 2 (#31, #40)", each number linking its `Note for` comment (F07 design 6.6, D284).
- **The links** go to the documents on `main` and to the dependencies' progress issues. The issue never holds a document's text or the summary for Troy (section 8.3).
- **No time stamps** that change at every sync, so a sync edits the body only when something changed.

### 4.3 Its timeline

The Why section of every stage PR's description starts with `Progress: #<n>`, and PR 6's with `Closes #<n>`, using `next.issue`. GitHub then lists each stage PR in the issue's timeline, with its title and whether it is open, merged, or closed, with no further write. PR 6's merge closes the issue even if the sync after it fails.

### 4.4 Kept up to date

The sync runs at every start and after every step, and edits the body only when it differs. troy-mode writes no comment on a progress issue except a reply to Troy (section 7) and a note for a later feature (F07 design 6.6), which it never edits or deletes. When Troy edits the body or the title, the next sync puts troy-mode's text back. When Troy closes the issue while the feature is not accepted, the next sync reopens it. To say something to troy-mode, Troy writes a comment.

### 4.5 Closed at acceptance

PR 6's merge closes the issue, as section 4.3 says. The next sync renders it once more, with six ticks and the feature's new status, such as "Ran for real on Troy's PC", and closes it as completed if it is still open. The sync renders it once more even when PR 6's `Closes #<n>` already closed it; it knows the issue is final when its `6/6` box is ticked. After that the sync leaves a closed progress issue alone. A later status, such as "Usable on Troy's devices" after the version's acceptance, shows in the requirements and on the version's checklist (section 6.2).

## 5. Idea issues (D143)

### 5.1 How Troy writes one

- **On GitHub, on the phone or the web,** Troy opens a new issue from the template "Idea / 想法", which adds the `idea` label. troy-init adds the template as `.github/ISSUE_TEMPLATE/idea.md` (section 11). Troy writes in any language, as much or as little as in a chat message.
- **An issue with no label** counts as an idea too. Every issue troy-mode opens has a label, so an unlabeled issue in a troy-mode project is Troy's. When the app does not offer the template, or Troy forgets it, nothing is lost: troy-mode adds the `idea` label when it answers.
- **More later.** Troy adds a comment. troy-mode sees new comments, not edits to the text Troy wrote first.

### 5.2 When troy-mode reads it

Nothing runs while Troy is away. At the next troy-mode run, `status` lists the new ideas (section 3.3) and gives the action `ideas` at the next natural stop:

- after the work already started: an open PR, a PR that records an approval or an acceptance, PR B of a bug, rework after a requirement change, an open release, a tag, a retrospective, and a rule's cleanup;
- and before the next new thing: the question about later approvals (F07 D62), a version test plan, a release that has not started, the first stage of a feature, or "every feature is accepted".

So an idea never interrupts a feature between its stages, and a requirement change comes before the next feature, which it may change. When Troy's request names an idea, such as "idea #101" or "change: #101", troy-mode takes it at once. When the request reaches no further (F07 D63), the ideas wait for the next run, and the report says how many are open.

### 5.3 What the Product Manager does with it

The main session, as the Product Manager (a new task, PM6), reads each new idea with its comments, decides what it is, and posts a comment that says so in the language Troy wrote in. The comment's first line is a fixed English heading, so the engine can tell troy-mode's comments from Troy's (F07 design 8.4):

| The idea is | Heading | What follows |
| --- | --- | --- |
| A requirement change | `Idea: requirement change` | The change, in a sentence or two. Then PM2, with the idea in Input, on `troy-mode/change-<slug>`. The change PR's description says `Closes #<n>` for each idea it takes in, and it waits for Troy's approval as every requirement change does (F07 design 11.2). Several ideas that change the same features may go into one change PR. |
| A bug | `Idea: bug` | The `bug` label replaces `idea`, and the issue becomes bug `B<n>` (F07 design 11.1). It waits for the bug flow: Troy asks for it, or the next release fixes it first (F08 D74). |
| A rule | `Idea: rule` | The rule change flow (F09), which asks Troy before anything is written (F09 D82). |
| A question, or something troy-mode will not change | `Idea: answered` | The answer, then the main session closes the issue. Something about troy-mode itself, rather than the project, is answered with what Troy can do: a rule for every project (F09 D83). |
| Meant for later, as Troy says in it | `Idea: later` | Nothing until Troy comments again or names it. |
| Unclear | `Waiting for Troy: <question>` | One question with a recommended answer. `status` lists it as waiting on Troy. |

Triage asks Troy nothing more than the flows already do: a requirement change waits for Troy's approval of its PR, and a rule waits for Troy's yes. Every other kind goes on without asking (requirements 3.3).

### 5.4 Closing

- **A requirement change:** the change PR's merge closes the idea. The main session then comments `Idea: in the requirements`, with the new or changed features and their progress issues once they exist.
- **Declined:** when Troy turns the change down, the main session comments `Idea: answered` with Troy's words and closes the idea.
- **A bug:** PR B's `Fixes #<n>` closes it (F07 design 11.1).
- **A rule:** the rule PR's description says `Closes #<n>`.
- **Answered:** closed with the answer.
- **Closed by Troy:** troy-mode does nothing more with it. If a change PR for it is open, troy-mode asks Troy whether to close that PR too.

### 5.5 Ideas from chat that wait

When Troy gives an idea in chat that troy-mode does not act on now, for example while a PR is open (F07 design 4, "One PR at a time"), or because Troy says "later", the main session opens an idea issue for it with Troy's words, so it is not lost when the session ends. A request troy-mode acts on at once gets no issue.

## 6. The device-test checklist (D144)

### 6.1 When it is created

At F08's step 5, Troy's test (F08 design 5.6), after a release test passed: `status` gives the release step `troy-test`, and the next sync creates the checklist. The main session then tells Troy in chat, as today, with the checklist's link.

- **One per version.** A new release test run, after bugs were fixed, changes the same issue (section 6.3).
- **A patch release** lists only the scenarios its fixes touched, which the main session names with `--device-test-scenarios` (F08 design 6).
- **A version with no scenario for Troy** still gets one, with only the accept box, so Troy can accept from the phone.

### 6.2 What it shows

The title: `v0.1.0 在你的设备上测试 / Test v0.1.0 on your devices`. The body, shortened:

```markdown
<!-- troy-mode: device-test v0.1.0 -->
**在你的设备上测试 v0.1.0** · 第 1 轮 · 要测的提交：34a7728
发布 PR：#94 · 更新记录 · 版本测试计划（链接）
功能：F01 到 F13，自动场景全部通过。

测完一项、结果和预期一样，就勾上它。哪一项不对，就不勾，写一条评论说明。全部通过后，勾最后一项。

- [ ] **v0.1-S24 安装发布版本，在两种 shell 里从任何文件夹运行。**
  设备：你的电脑。
  步骤：1. … 2. … 3. …
  预期：两个标签页都显示 `recipe-menu 0.1.0`。
- [ ] **v0.1-S25 Windows Terminal 里中文显示正确。** …
- [ ] **v0.1-S26 在手机上勾选购物清单。** …
- [ ] **我接受 v0.1.0。**

<details><summary>English</summary>

**Test v0.1.0 on your devices** · run 1 · commit to test: 34a7728
...
v0.1-S24 Install the release and run it from any folder, in both shells.
Device: your PC. Steps: 1. … Expected: …
...

</details>
```

- Each scenario Troy runs, from the version test plan's sections 2 and 3, with its ID, title, device, steps, and expected result. The Chinese text comes from the plan's mirror and the English from the plan, both as written. The plan stays the source; the checklist is a copy for the phone.
- The commit to test, from the release test's comment `Release test, run <n>: passed`, and links to the release PR, the changelog section, and the plan.
- The version's features, as one line, with their statuses.
- The accept box last. troy-mode never ticks a box of the checklist.

### 6.3 Ticks, failures, and acceptance

| Troy | troy-mode, at its next run |
| --- | --- |
| Ticks every scenario and the accept box | `device_test.result` is `ticked`. The main session posts `Release test by Troy, run <n>: accepted` on the release PR, with Troy's comments on the checklist as Troy's notes, and goes on with the acceptance (F08 design 5.7). |
| Leaves a scenario unticked and writes a comment | The main session reads the comment. A failure is recorded as `Release test by Troy, run <n>: failed` with Troy's words, and goes to the Test Manager's triage (F08 design 5.8). A question or a note gets a `Reply to Troy`. |
| Ticks the accept box while a scenario is not ticked | `result` is `incomplete`. The main session asks Troy which is meant, with `Waiting for Troy: <question>` on the checklist and in chat. |
| Ticks some boxes and stops | Nothing changes. The release keeps waiting for Troy. |

**A new run.** After bug fixes, the release test runs again (F08 design 5.8). When it passes, the sync updates the checklist: the run number and the commit; the accept box cleared; the scenarios named in the `Release test by Troy, run <n>: failed` comment unticked; and Troy's other ticks kept, because Troy tests again only what failed (F08 D74). The main session posts `Device test, run <n>: ready` on it, naming the scenarios to test again, and tells Troy in chat.

### 6.4 Chat still works

Troy can still reply in chat or on the release PR, as today (F08 design 5.6). An acceptance given there needs no ticks. The checklist then closes with the release.

### 6.5 Closed with the release

Once the release PR has merged, the next sync closes the checklist as completed. Its ticks and comments stay as the record of Troy's test, next to the acceptance record in the version test plan.

## 7. Replies from the phone (D145)

Nothing runs while Troy is away. Troy's edits and comments wait for the next troy-mode run on the PC, such as `/troy-pstack:troy-mode continue`, and `status` reads them first.

| On the phone, Troy | troy-mode, at its next run |
| --- | --- |
| Opens an issue, from the template or with no label | An idea (section 5). |
| Comments on an idea | Read with the idea: more detail, or the answer to troy-mode's question. |
| Comments on a progress issue | Read as a message in chat. A question gets a `Reply to Troy` comment. A remark about the open PR goes to that PR's author as Input, as Troy's PR comments do today (F07 design 8.4). A new request is handled as an idea. |
| Comments on a PR that waits for Troy, or leaves a "Comment" review on it | Troy's reply, exactly as in chat: "全按推荐", "all as recommended", or "approved" approves the PR; picking another option asks for changes (F07 D61, F14 design 5.4). The description's What says that Troy approved in a comment. |
| Comments on another open troy-mode PR | Input for its author, as today. |
| Merges a PR that waits for Troy | As today: troy-mode records the approval in a `[docs]` PR (F07 D61). |
| Ticks boxes or comments on a device-test checklist | Section 6.3. |
| Edits troy-mode's text or title, or closes a progress issue or a checklist | Replaced, or reopened, at the next sync (section 4.4). |
| Closes an idea | Section 5.4. |

troy-mode answers a comment on an issue in the language Troy wrote it in, under a fixed English heading (section 8.4). Comments on PRs stay in English, as today.

## 8. Labels, language, and what an issue holds (D146)

### 8.1 Labels

| Label | On | Color | Description |
| --- | --- | --- | --- |
| `idea` | Troy's ideas | `FBCA04` | `An idea or change for troy-mode to take in / 交给 troy-mode 的想法或改动` |
| `progress` | Progress issues | `1D76DB` | `A feature's progress, kept by troy-mode / 功能进度，由 troy-mode 维护` |
| `device-test` | Device-test checklists | `0E8A16` | `What Troy tests on Troy's devices for a release / 发布前 Troy 在自己设备上测的项目` |

- `bug` stays as F07 uses it. GitHub creates it in every new repository.
- The main session creates a missing label from `issues`' report. It never changes a label that exists, so a label Troy made keeps its color.
- The engine finds troy-mode's issues by label and by the first line of the body, `<!-- troy-mode: progress F04 -->` or `<!-- troy-mode: device-test v0.1.0 -->`, which GitHub does not show. A title Troy changes does not lose the issue.

### 8.2 Language

Troy reads these issues on the phone, in Chinese first, as with the summary for Troy (F14 D135):

- **Bodies** have the Chinese part first and the English part inside a folded "English" block. The boxes are in the Chinese part only, so each box exists once.
- **Fixed words,** such as stage names, review results, and "Waiting for you", come from one table in the engine, in both languages.
- **Text from documents,** such as feature names, statuses, and scenario steps, comes from each document and its mirror.
- **Titles** hold both, Chinese first.
- **troy-mode's comments on issues** are in the language Troy wrote in, under an English heading. PR comments stay in English.
- **The idea template** asks in both languages.

### 8.3 What an issue holds and what it links to

| Holds | Links to |
| --- | --- |
| Lines built from the state: stages, PR numbers, review headings, statuses, what waits on Troy | Every document on `main`: requirements, designs, test plans, version test plans, the changelog, prototypes |
| Troy's scenarios, copied from the version test plan and its mirror | The PRs, by number, and the summary for Troy at the top of a PR's description |
| troy-mode's short comments: triage, replies, a new run | The real-run report in PR 6's description |

- **Never in an issue:** a document's text beyond Troy's scenario rows, the summary for Troy, code, logs, local paths that the documents do not already hold, and secrets (requirements 8, Privacy).
- **Size.** The engine keeps every body under 60,000 characters, below GitHub's 65,536 (section 2). When the checklist's copied steps would pass it, each scenario keeps its ID, title, and expected result and links to its row in the plan for the steps, and `issues` reports the shortening in `problems`. `check-text` refuses a file over 65,536 characters (section 10.1). The pilot's checklist would hold about 4,000 characters.
- **Links** are full URLs, `https://github.com/<owner>/<repo>/blob/main/<path>`, because relative links do not work in issues.

### 8.4 troy-mode's comment headings on issues

Each starts the comment's first line, so `status` can tell troy-mode's comments from Troy's:

- `Idea: requirement change`, `Idea: bug`, `Idea: rule`, `Idea: answered`, `Idea: later`, and `Idea: in the requirements` (section 5);
- `Waiting for Troy: <question>` (F07's heading);
- `Reply to Troy`;
- `Device test, run <n>: ready` (section 6.3);
- `Note for <feature ID>, from <source>`, on progress issues, in English, since roles read it (F07 design 6.6).

## 9. When gh or the network fails (D147)

Progress issues and checklists are views. The flow never stops because one of them could not be written, and the next sync repairs it. What troy-mode reads from Troy is never guessed.

| What fails | What troy-mode does |
| --- | --- |
| Creating a label, or creating, editing, closing, or reopening an issue | Notes it with `status --note "Issue sync failed: <what>"`, says so in its next report to Troy, and goes on. The next sync rebuilds the view and tries again. |
| The agent's permissions refuse a `gh issue` or `gh label` command | Tells Troy once which permission rule to add, such as `Bash(gh issue *)` and `Bash(gh label create *)`, and goes on as above. It never works around a refusal. |
| `check-text` fails on a body or a comment | Nothing is posted. A body the engine rendered is troy-mode's own error, and troy-mode tells Troy. A comment is reworded. |
| `status` cannot read the issues | `issues.error` holds why. No `ideas` action and no acceptance from the checklist. The rest of `status` works, and the flow goes on. |
| `gh` or GitHub is down altogether | As today: `status` needs `gh` for the PRs and stops with exit code 2, and no PR can merge. |
| The repository has issues turned off | `issues` reports it in `skipped`, and F15 does nothing there. Chat works as before. |
| A create succeeded but its answer was lost, so two issues exist for one feature or version | The next sync finds both by their first line, keeps the older, and closes the newer as "Duplicate of #<n>". |
| The checklist cannot be created | The main session tells Troy the scenarios in chat, as F08 does today, and Troy replies in chat. |
| Troy ticks a box while troy-mode edits the checklist | troy-mode edits a checklist only when a new run starts, after Troy reported a failure and waits for fixes, so this is rare. The tick may be lost; Troy sees it unticked and ticks again. |

## 10. Checks and hooks (D148)

### 10.1 `check-text`

- The main session checks every body file and every comment with `troy_flow.py check-text --file <file>` before it posts, and reads its exit code. In #92 the output was read instead, and a failed check was posted.
- `check-text` also fails when the file holds more than 65,536 characters, so a post GitHub would refuse is caught first.

### 10.2 F05's `gh` guard

troy-pstack's issue #65, which Troy approved on 2026-11-16, widens R19 and F05's guard: before the main session posts it, the hook checks the text of `gh issue create`, `gh issue edit`, `gh issue comment`, `gh pr comment`, `gh pr review`, `gh pr merge`, `gh release create` and `edit`, and `gh api` with fields, and fails closed on text it cannot read. F15 posts through these commands and needs that check. F15 adds to its table:

| Command | Text the hook checks |
| --- | --- |
| `gh issue close`, `gh issue reopen` | `--comment` and `-c` |
| `gh label create`, `gh label edit` | `--description` and `-d` |

And it refuses, for every caller in a troy-mode project, `gh issue delete` and `gh label delete`: deleting is irreversible and outside troy-mode's rights (F07 design 9).

Roles stay read-only on GitHub. F05's list for subagents allows `gh issue view`, `gh issue list`, and `gh issue status` only (F05 design 7.3), so no role writes an issue.

### 10.3 What else checks it

- **No new R rule.** R19, as #65 widens it, covers issues and comments. troy-check's CI checks change nothing, because an issue never enters the repository.
- **The idea template** lives in `.github/`, in the `config` path class, which R20 does not scan (F06 design 4.2).
- **The engine's tests** check every rendered body, every parsed tick, and every sync decision exactly (section 13.1).
- **Not checked:** whether the main session's triage is right, and whether a reply is plain enough. Troy reads both.

## 11. Location and changes to earlier features

```text
skills/troy-mode/SKILL.md          a new section "Issues for Troy" (sections 3 to 9); Start, One stage, Merging, Version release, Comments, Escalation, Routing, and Continue
troy-mode/
  flow/
    troyflow/                      the issues command and its modules (the Developer's choice)
    troyflow/github.py             issue reads, the new comment headings, Troy's PR reviews
    troyflow/status.py, nextstep.py   the issues part, next.issue, and the ideas action
    troyflow/textcheck.py          the length check
    troyflow/cli.py                the issues command
    tests/                         the tests of section 13.1
  templates/
    progress-issue.md              new: the progress issue's shape, both languages
    device-test-issue.md           new: the checklist's shape, both languages
    idea-issue.md                  new: GitHub's issue template for ideas
    README.md, .zh-CN.md           list the three
  roles/product-manager.md         PM6 Ideas; PM2 takes an idea as its input
  init/troyinit/                   setup and upgrade write .github/ISSUE_TEMPLATE/idea.md
  hooks/troyhook/ghcmd.py          the commands of section 10.2
docs/troy-mode/guide/              pages 01, 03, 04, 05, 07, and 08, in both languages
.claude-plugin/plugin.json         the next minor version (section 12)
```

| Feature | Change |
| --- | --- |
| F01 Templates | Three new templates. `progress-issue.md` and `device-test-issue.md` give the bodies' shapes, which the engine renders in code, as `progress.md` gives the progress file's. Each holds both languages, Chinese first, like `summary-for-troy.md`. `idea-issue.md` is GitHub's issue template: front matter with `name: Idea / 想法`, `about`, and `labels: idea`, and two lines that ask for the idea in any language. The README's table lists them. |
| F04 Roles | The Product Manager's new task PM6, Ideas: when, the kinds of section 5.3, and the headings. PM2 takes an idea issue as its input, and its PR says `Closes #<n>`. No agent file changes. |
| F05 Hooks | The commands of section 10.2, on top of #65's change. `hooks.json` does not change. |
| F06 troy-init | Setup and upgrade write `.github/ISSUE_TEMPLATE/idea.md` from `idea-issue.md`, as they write `.github/pull_request_template.md`, under the same hash rule (F06 design 6). troy-init creates no label. |
| F07 Entry skill | The engine's `issues` command and the parts of `status` (section 3). The skill: "Issues for Troy"; Start runs the sync; One stage's step 5 puts `Progress: #<n>` or `Closes #<n>` first in Why, and step 8 runs the sync; Merging takes Troy's reply from a PR comment or review (section 7); Comments lists the issue headings; Escalation's rights gain issue and label writes; Routing gains "idea #<n>"; Continue gains `ideas`. `check-text` gains the length check. |
| F08 Release | Step 5 creates the checklist through the sync, and a `ticked` checklist is Troy's acceptance. A new run updates it (section 6.3). The release step's text in `status` names the checklist. |
| F10 Guide | `01-install.md`: the permission rules of section 9. `03-features.md`: the progress issue. `04-bugs-and-changes.md`: ideas. `05-release.md`: the checklist. `07-taking-part.md`: working from the phone, and that GitHub sends no notification for troy-mode's writes. `08-reference.md`: the labels, the `issues` command, and the headings. Each in both languages. |

No upstream pstack file changes. F02, F03, F09, F12, F13, and F14 do not change.

## 12. Existing projects and the plugin version (D149)

F15's build PR raises the plugin's minor version, to the next free one when it merges: 0.6.0 if nothing has raised it first (F10 D89). F19 took 0.6.0 and #65 0.6.1, so F15 brings 0.7.0. Then:

1. **Troy updates the plugin** and restarts Claude Code (F10 design 6). When #65's change lands the same day, one update brings both.
2. **The first troy-mode run in a project** creates the labels and the progress issue of the current or next feature, and reads Troy's ideas. It needs no file in the project: the skill, the engine, and the hooks come with the plugin.
3. **`upgrade troy-mode`** brings the idea template and the new templates, through troy-init's `[rules] Upgrade troy-mode to <version>` PR, which troy-init merges (F06 design 6). Until then, Troy writes an idea as an issue with no label. `status` notes when `.github/ISSUE_TEMPLATE/idea.md` is missing on `origin/main`, because its check of the project's copy covers troy-check only.
4. **No backfill.** Accepted features get no progress issue, released versions get no checklist, and earlier chat ideas get no issue.

For `ZJUCao/recipe-menu`: v0.1.0 is released, and v0.2 holds F14 to F16, not started. After the update, the first run creates the three labels and F14's progress issue, with nothing ticked. v0.2's release brings the first checklist. If the desktop app's auto mode refuses the `gh issue` commands, Troy adds the rules of section 9, as the pilot did for the amend and the force push (troy-pstack #50).

## 13. How F15 is checked (D150)

### 13.1 Tests

A separate agent writes the tests from this design, before the code exists, with F07's setup: a temporary git repository with a local bare `origin`, and a fake `gh` on the `PATH` that serves PRs, comments, reviews, issues, and labels from a JSON file and records its calls (F07 design 14.1).

| Group | Cases include |
| --- | --- |
| Progress issues | Created for the next feature with nothing ticked, and for a feature with a stage PR. Ticks from merged stages, with rebase, squash, and merge-commit subjects. The skipped mock. Rework and a redo. The open PR's last review heading, translated. "Waiting for you" from a `Waiting for Troy` comment. Side PRs and real-run bugs listed. No edit when nothing changed. Edited after Troy changed the body or the title. Reopened after Troy closed it. Closed as not planned when no longer next, and reopened when next again. Closed as completed after PR 6. Never created for an accepted feature. |
| Ideas | An `idea` label and an unlabeled issue count; `bug`, `progress`, and `device-test` issues do not. `new` until troy-mode's heading comment, and again after Troy writes. The `ideas` action before a feature's first stage, a version test plan, a release not started, and `all-accepted`; never between two stages, during an open PR, or during an open release. |
| Checklist | Created at `troy-test` with Troy's scenarios of sections 2 and 3, in both languages, and the accept box last. A patch's named scenarios kept across syncs. Only the accept box when no scenario is Troy's. Results `waiting`, `ticked`, and `incomplete`. Ticks alone cause no edit. A new run clears the accept box, unticks the failed scenarios named in the failed comment, keeps the others, and changes the commit. Closed after the release PR merges. |
| Labels and text | A missing label gives its create command; an existing one is never changed. Both languages, Chinese first, the boxes once. No time stamp. Full URLs. A body over 60,000 characters shortened, with a problem. Duplicates closed, the older kept. Issues turned off: skipped. |
| Reading Troy | Comments and reviews on a PR waiting for Troy end the wait and reach `troy_comments`. Troy's comments on progress issues and checklists. Every new heading of section 8.4 is troy-mode's. A `Note for` comment after Troy's comment leaves Troy's comment in `troy_comments`. |
| Notes (F07 D284) | The notes line on the target's progress issue, in both languages, with a link per note, and none without notes. A note on a closed progress issue still counts. |
| `check-text` | A file of 65,537 characters fails, one of 65,536 passes. |
| Hooks | Each command of section 10.2, long and short forms, refused with attribution and passed without. `gh issue delete` and `gh label delete` refused for the main session and for roles. |
| Skill, templates, init | The skill names `issues`, the headings, and the steps of section 3.4. The three templates and their README rows. Setup and upgrade write the idea template, and upgrade replaces it only when unchanged. |

### 13.2 Planted bugs

After the code passes, bugs are planted one at a time in a scratch copy, and each must make a test fail. They include: a progress issue created for an accepted feature, a stage ticked from an open PR, the skipped mock left unticked, a body edited when nothing changed, Troy's closing left in place, a closed progress issue edited again, an unlabeled issue not counted as an idea, a `bug` issue counted as one, the `ideas` action between two stages, Troy's ticks lost at a sync, the accept box kept at a new run, `ticked` with one scenario unticked, a checklist ticked by the engine, a missing label used before it exists, an existing label changed, the size limit counted in bytes, the newer duplicate kept, a Troy review on a waiting PR ignored, `check-text`'s length check off by one, and `gh issue close --comment` let through unchecked. F07's D284 to D287 add: a note counted as troy-mode's answer to Troy, and a note's line shown on the source feature's issue instead of the target's. The counts go in the build PR's description.

### 13.3 Trial

Before the build PR opens, F15 runs in nested `claude -p` sessions on Troy's PC, with troy-pstack loaded from the PR branch, on `ZJUCao/troy-mode-trial`, under Troy's standing permission for troy-mode trials (F08 design 11.3). #65's change must be in the plugin first. The trial script acts as Troy's phone: it opens issues, comments, and ticks boxes with `gh`, as Troy, and the trial's answer file gives Troy's chat answers.

1. **First sync.** The first run creates the three labels and F02's progress issue, with stage 1 ticked (PR #29) and stage 2 next.
2. **Upgrade.** "upgrade troy-mode" brings the idea template through its PR.
3. **Ideas.** The trial script opens two issues: one with the `idea` label, asking for a `--lines` option of `wordcount` in a new version v0.3, and one with no label, asking whether `count_lines` reads the whole file at once. troy-mode answers the second and closes it, and turns the first into a change PR that says `Closes #<n>`. Troy approves it in the answer file. It merges and closes the idea.
4. **F02's stages 2 to 6.** The progress issue changes at each step, each stage PR starts with `Progress: #<n>`, and PR 6 closes it. Between two stages, the trial script edits the issue's body and closes it, as a stray tap would, and comments a question in Chinese. The next sync restores and reopens it, and troy-mode answers in Chinese under `Reply to Troy`.
5. **A refused write.** One session runs with `--disallowedTools "Bash(gh issue edit:*)"`. troy-mode reports the refusal and the rule to add and goes on, and the next session catches up.
6. **Release v0.2.0.** A prepared `[docs] Update the v0.2 test plan` PR, made before the trial, adds one scenario that Troy runs: `wordcount` on a file with Chinese text, read in Windows Terminal. After the release test passes, the checklist appears and the session stops. The trial script ticks the scenario and the accept box, as Troy's phone would. A new session gets "continue", reads the ticks, records the acceptance on the release PR, merges it, creates the release, and closes the checklist.
7. **Facts.** From the transcripts and GitHub: every body passed `check-text` before it was posted, no session asked Troy anything the answer file did not cover, and each issue's timeline lists its PRs. If a fact differs from this design, the design is updated in the build PR.

It takes about 13 role runs: TM1 with IF3, DV1, CR1, TE1, TM2, CR1, DV2, CR1, then TE5, TM2, and CR1 for the version tests, and AR4 when the change needs it. That is about $13 to $20 from F08's trial, plus Actions minutes for about 11 PRs. If Troy is at the PC during the trial, Troy ticks one box of its checklist in the GitHub app, which shows whether the app ticks boxes in an issue; otherwise v0.2 of the pilot shows it. The repository, its issues, and its release stay. Deleting them is Troy's call.

### 13.4 Status

| When | F15's status in requirements 7.2 |
| --- | --- |
| The build PR merges after a passing trial | Runs on a sample project: on a scratch GitHub project, troy-mode kept a feature's progress issue through its six PRs, turned two issues Troy opened into a change and an answer, and accepted a version from a checklist that Troy's ticks filled in. Not yet used on a real project. |
| The pilot has a progress issue, an idea, or a checklist | Used on a real project: <which issues of `ZJUCao/recipe-menu`, and what Troy did with them>. |

If the trial cannot run before the PR, the status is "Written" until it does. The status update is its own PR.

### 13.5 What the trial showed (2026-11-17)

The trial ran on `ZJUCao/troy-mode-trial` in seven nested sessions, with tstack loaded from the build branch and the installed plugin turned off. It cost $18.56 at list prices, within the estimate, with 15 role runs (DV1, CR1; TE1, TM2, and CR1 twice each, DV2, CR1, AR4; TE5 twice, TM2, CR1).

| Step | What happened |
| --- | --- |
| 1. First sync | The labels `idea`, `progress`, and `device-test` and F02's progress issue #49: stage 1 ticked (#29), stage 2 open (#48), "Waiting for you: approve #48". |
| 2. Upgrade | `[rules] Upgrade troy-mode to 0.7.0` (#50) brought `.github/ISSUE_TEMPLATE/idea.md` and #65's R19 text, and merged. |
| 3 and 4. Ideas and F02 | Troy's approval of #48 in chat; the mock (#54), tests (#55), implementation (#56), and acceptance (#57). Each stage PR's Why started with `Progress: #49`, PR 6's with `Closes #49`, and #49's timeline lists #48 and #54 to #57. Between two stages, the trial script edited #49's text, closed it, and asked a question in Chinese: the next session reopened it and answered in Chinese under `Reply to Troy`. The two ideas waited while F02 was between stages. After F02's acceptance, the same session took them in: #52 (no label, a question in Chinese) got `Idea: answered` and was closed; #51 (`idea`) became change PR #58 with `Closes #51`, which merged on Troy's approval, and `Idea: in the requirements` named F05 and its progress issue #59. |
| 5. A refused write | The session of steps 3 and 4 ran with `gh issue edit` refused. It named the rule to add, noted the failures, and went on; the next session rendered #49 once more as final (6/6) and left it closed. |
| 6. Release v0.2.0 | Version tests #60, release PR #61, and the release test passed on Troy's PC; the sync created checklist #62 with Troy's scenario v0.2-S18 and the accept box. The trial script ticked both. The next session posted `Release test by Troy, run 1: accepted` on #61, merged it, created the GitHub release v0.2.0, and closed #62 as completed. |
| 7. Facts | Every one of the 40 posts with a body file was checked with `check-text` first, and its exit code read. The hook refused two `gh pr create` calls whose file was named by `$(git rev-parse --absolute-git-dir)/...`, as section 8.2 of F05's design says, and the session posted with the path. No session asked Troy anything the answer file did not cover. |

**Where the trial differed from section 13.3.**

1. The repository had moved on: `main` at `2c2940c`, F02's test plan PR #48 open and waiting for Troy, tstack 0.6.0, and `troy_approves_first = 4`. So the first sync showed stage 2 waiting for Troy, and Troy's approval of #48 was given in the request of the third session.
2. The ideas were opened after the upgrade, while F02 was between stages. Following D143, troy-mode took them in after F02's acceptance, so step 3 came after step 4. The session that accepted F02 went on to the ideas, judging that "continue" reached that natural stop.
3. The refused write (step 5) ran in the same session as F02's last stages and the ideas.
4. The prepared `[docs] Update the v0.2 test plan` PR (#53) also changed v0.2-S11, v0.2-S12, and v0.2-S17 to exit code 2 for a file error, which F04's design and ADR-0002 had decided; the plan still expected 1, known since F12.
5. The release session stopped at the plan's 5-hour usage limit during TE5 and was resumed with `--resume`; it ran TE5 again from the cut-off draft.
6. Troy was not at the PC, so the optional tick in the GitHub app did not run.
7. The first three sessions used an earlier build of the branch: two template files held garbled characters, which only their reference text shows, and a tick written `[X]` caused an edit. Both were fixed before the fourth session.

**What the trial changed in the build.** The checklist copies each scenario's cells as written, code marks included: #62 had dropped the plan's backticks, as the engine's table reader removes them, and a test now checks them. A progress issue's title is `<ID> <name>` when the mirror gives the same name, as in the trial's requirements. The hook's refusal of a file named by `$(...)` now says so, and the skill says to name a body file by its path.

**Follow-ups, not fixed here.** After the release PR merged, `status` still carried "PR #61: Waiting for Troy: accept v0.2.0" in `waiting_on_troy`, from the progress file's carried text (F08's release flow). A refused `gh issue edit --add-label idea` is not tried again, so #52 kept no label. In the trial project, F02's test plan row F02-T09 lost a U+2028 character of the design's example file.

## 14. How F15 maps to the requirements

| Requirement | Where F15 covers it |
| --- | --- |
| F15 row: an issue with the `idea` label for each new idea or change request, which the Product Manager turns into a requirement change | Section 5 |
| F15 row and 3.3: one progress issue per feature, with its six PRs as a checklist, updated at each stage and closed at acceptance | Section 4 |
| F15 row and 5.5 step 3: one checklist issue per version, ticked while testing | Section 6 |
| F15 row: documents stay in the repository | Sections 1 and 8.3 |
| 3.3: where Troy takes part; every other step goes on without asking | Sections 5.3 and 7 |
| 5.4 step 1: a change asked for in an idea issue | Sections 5.2 and 5.3 |
| 5.10: continuing from the state | Sections 3.1 and 4.4 |
| Section 6, R19 | Section 10 |
| Section 8: Privacy, Resumable, and Language | Sections 8.2, 8.3, and 9 |
| Q10: one PR per feature | Section 1 |

## 15. Not in F15

- Starting troy-mode from the phone, or a session that wakes up when Troy edits an issue. Troy's phone edits wait for the next run on the PC.
- Notifications. troy-mode acts through Troy's account, and GitHub does not notify Troy of Troy's own activity. A separate account for troy-mode would change F04 D29.
- Pinned issues, milestones, GitHub Projects boards, and sub-issues.
- Issues for rule changes, cleanups, version test plans, or the work outside the pipeline.
- Issues in troy-pstack, other than F09's rule proposals.
- Building #65's change itself, which comes first (section 10.2).

## 16. Decisions for Troy

F12, F13, and F14 use D101 to D137, D151 onward are kept for F16, and D191 onward for F19, so F15 uses D141 to D150. Troy accepted every recommended answer on 2026-11-16.

| ID | Question | Options | Recommended and approved |
| --- | --- | --- | --- |
| D141 | Who writes the issues, and when? | A: a new engine command, `issues`, works out every progress issue and checklist from the state and writes their bodies to files with the `gh` commands; the main session checks each file and posts it, at every start and after every step. `status` reads Troy's ideas, comments, and ticks (section 3). B: the engine creates and edits the issues itself. C: the main session writes and updates every issue from the skill's instructions. | A. The engine stays read-only on GitHub (F07 design 3.1), every post goes through `check-text` and F05's guard, which do not see a program's own `gh` calls, and tests can check each body exactly. C depends on memory across long sessions, which the pilot compacted 10 times. |
| D142 | When does a feature's progress issue exist, and what does it show? | A: from the moment the feature is next or has a stage PR, until acceptance. The body is rebuilt from the state: the six stages as boxes, the open PR's last review, what waits on Troy, and links. Each stage PR says `Progress: #<n>`, so GitHub lists it in the issue, and PR 6 says `Closes #<n>`. Troy's edits are replaced, and Troy writes in comments (section 4). B: as A, but created only when PR 1 opens. C: one issue for every feature of the requirements at once. | A. Troy sees on the phone what comes next, and only the features in play have open issues. B hides the next feature until its first PR. C opens many issues at once that stay empty for weeks; the pilot's 16 features would make 16. |
| D143 | How does troy-mode find Troy's ideas, and when does it act on them? | A: an issue opened from the "Idea" template, which adds the `idea` label, or any issue with no label. At the next natural stop, before a new feature, a release, or a version test plan starts, never between two stages, the Product Manager answers each new idea with what it is and goes on: a requirement change through its PR, which closes the idea and waits for Troy's approval; a bug, a rule, an answer, or "later". An idea Troy gives in chat that waits gets an issue too (section 5). B: troy-mode reads ideas only when Troy names one in chat. C: as A, but acting at once, between stages too. | A. An idea Troy writes on the phone is acted on at the next run without Troy repeating it, and a change comes before the feature it may change. Troy still approves every requirement change. C would reopen work in the middle of a feature. |
| D144 | How does the device-test checklist work, and how does Troy accept a version with it? | A: one issue per version, created after the release test passes, with one box per scenario Troy runs, its steps and expected result copied from the plan, and a last box "I accept". All boxes ticked is Troy's acceptance; a failure is a comment. A new run keeps Troy's passed ticks and clears the rest (section 6). B: as A, but acceptance only in chat; the boxes are Troy's notes. C: create it when the version test plan merges, before any feature of the version starts. | A. Troy tests on the phone and accepts there, with no table to scroll. Chat and the release PR still work. B makes Troy come back to the PC only to say a word. C shows boxes months before there is anything to test. |
| D145 | How do Troy's replies from the phone come back? | A: at the next troy-mode run, Troy's comment on a PR that waits for Troy, or a "Comment" review, counts as Troy's reply in chat; comments on progress issues are read like chat messages; Troy's edits to troy-mode's text are replaced, and a closed progress issue or checklist is reopened (section 7). B: as A, but approvals stay in chat or by merging; a PR comment only goes to the author as Input. | A. Approving from the phone is the point of F15, and F08 already takes a release reply from a PR comment. The same words work in both places: "全按推荐" approves. |
| D146 | Which labels, which language, and what may an issue hold? | A: labels `idea`, `progress`, and `device-test`, created by the main session when missing and never changed once they exist. Bodies are Chinese first with the English folded below. An issue holds lines built from the state and Troy's scenarios copied from the plan; everything else is a link. Bodies stay under 60,000 characters (section 8). B: as A, but English only, as PR comments are. C: labels with a prefix, such as `troy-mode:progress`. | A. Troy reads these on the phone, in Chinese first, as F14 decided for the summary. Short labels are easy to filter on a phone. The checklist's steps must be on the phone, and nothing else needs to be. |
| D147 | What happens when `gh` or the network fails? | A: issues are views. A failed write is noted, reported, and repaired by the next sync; the flow goes on. A permission refusal is reported with the rule to add. Unreadable ideas or ticks are never guessed: no idea is acted on and no acceptance is taken until they can be read. Duplicates are closed (section 9). B: any issue failure stops the flow and escalates. C: retry each write a few times, then go on. | A. A progress issue that is a few minutes late costs nothing, and the next sync puts it right. B would stop a feature for a view. C adds waits when GitHub is down, which the next sync covers anyway. |
| D148 | How is issue text checked, and which hooks change? | A: troy-pstack #65's widened guard lands first, in its own PR, and F15's build adds `gh issue close` and `reopen` comments and `gh label create` and `edit` descriptions to it, and refuses `gh issue delete` and `gh label delete`. The main session checks every body and comment with `check-text` and reads its exit code; `check-text` also refuses more than 65,536 characters. No new R rule (section 10). B: F15's build includes all of #65. C: `check-text` in the skill only, with no hook change. | A. Text sent to GitHub keeps its edit history, so the check must come before the post, and #65 already designs it. Keeping #65 in its own PR keeps each PR to one change. C is how #92's comment got through. |
| D149 | How do existing projects get F15? | A: the next minor plugin version. The first troy-mode run after the update creates the labels and the current feature's progress issue, with no project file needed. `upgrade troy-mode` brings the idea template; until then an issue with no label is an idea. No backfill for accepted features or released versions (section 12). B: as A, plus closed progress issues for every accepted feature. C: F15 starts only after `upgrade troy-mode`. | A. F15 lives in the plugin, so the pilot gets it with no pause, and its v0.2 starts with F14's progress issue. B makes 13 issues for the pilot at once that nobody reads. C delays the progress issues for one template file. |
| D150 | How is F15 checked, and when does its status move? | A: tests from this design by a separate agent, planted bugs, and a trial on `ZJUCao/troy-mode-trial` that turns two of Troy's issues into a change and an answer, takes F02 through its stages with its progress issue, and releases v0.2.0 from a ticked checklist; about 13 role runs and $13 to $20 (section 13). Status after the merge: "Runs on a sample project". B: tests, planted bugs, and a short trial of the first sync, the ideas, and F02's stage 2 only; about 3 role runs. Status "Written" until the pilot. C: tests only. | A. The checklist and the acceptance from ticks are the riskiest part, and only a real release shows them. It also finishes the trial repository's v0.2, which has waited since F12. |

Requirements 1.39 records the approved changes:

- The F15 row says what F15 builds (D141 to D150).
- 3.3: Troy can answer a PR or an issue from the phone with a comment, and troy-mode reads it at its next run (D145).
- 5.4 step 1: troy-mode takes an idea issue in at the next natural stop, and the change PR closes it (D143).
- 5.5 step 3: the checklist issue appears after the release test passes, and ticking its last box accepts the version (D144).
- 5.10: each feature's progress issue is a view rebuilt from the state, like the progress file (D142, D147).
- Section 8, Privacy: no secret goes into an issue either (D146).

## 17. Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-11-16 | First draft, with two probes on `ZJUCao/troy-mode-trial` (section 2). |
| 1.0 | 2026-11-16 | Approved by Troy with D141 to D150, every recommended answer. |
| 1.1 | 2026-11-17 | Facts from the build and its trial: status's two reads (section 3.3), the final render after PR 6 (4.5), the title when the mirror gives the same name (4.2), the version 0.7.0 (12), and the trial's record (13.5). |
| 1.2 | 2026-11-22 | F20's design (D268 to D279, approved by Troy on 2026-11-22): every feature that may start has its progress issue, not only the next feature (section 4.1). The change lands with F20's build. |
| 1.3 | 2026-11-23 | F07's D284 to D287, from tstack issue #67, approved under Troy's standing yes of 2026-11-22: troy-mode's `Note for <ID>` comments on progress issues hold the notes for later features; the target's issue shows a notes line; a note never hides Troy's comment (sections 3.3, 4.2, 4.4, 8.4, 13.1, and 13.2). |
