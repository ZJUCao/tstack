<!--
template: The summary for Troy. It opens the description of every interface design PR (PR 1), test plan PR (PR 2), requirements PR, and architecture PR, before Why (rule R22). The role that writes the document fills it in its report's For Troy field, and the main session copies it into the description unchanged. The Chinese part comes first and says the same as the English part, which is the source.
Parts. Each language has the same three ### parts, under these headings, in this order, each with text under it:
  What changes for you (对你有什么变化): what Troy will type, see, or do differently once the PR's content is built: new commands and options, changed output, new files Troy edits, and what stays the same. For a test plan: what the tests check of that, what they leave out, and anything Troy runs by hand. For the architecture: what Troy will notice, such as speed, the files the program keeps, tools to install, and what will be hard to change later. For the requirements: what the program will do, or do differently.
  What you decide (需要你决定的事): one numbered item for each point Troy decides, then the fixed reply line. Each item: what is decided, in a few bold words; the options, as what Troy would see under each; "Recommended:" ("推荐：") with the option and why, in one sentence. Number the items in the order the document gives its points, so a reply such as "2: option 2" leads back to the document's second point. An item may go on in lines under it, such as one line per option. When a point has a single proposal, such as new texts to accept, show it and recommend it: Troy can still answer with other words. For new texts, show those Troy is most likely to want changed, and say how many the document lists in all. A point Troy already decided, for example in the design, is not asked again. Both languages have the same number of items. With nothing to decide, write only "Nothing to decide." ("没有需要你决定的事。"), with no item and no reply line.
  Risks (风险): what could go wrong for Troy, how likely it is, and what happens then. "None found." ("没有发现风险。") when there is none.
Length. At most 2,000 characters in each language, or the project's [summary] max_chars in .troy-mode/config.toml, counted from the line after the ## heading to the next ## heading, Markdown and line breaks included. A Chinese character and a letter each count as one. Leave a margin: the main session's check counts exactly, and a part over the limit comes back to you. With many points, say each one more shortly.
Plain words:
  1. Write for Troy as a user. Say what Troy types, sees, or must do. Do not say how the code is built.
  2. No internal IDs: no rule, decision, question, test case, scenario, ADR, performance target, or task IDs, and no section numbers. Name the thing instead: "the 1-second limit for search". Feature IDs such as F10, bug numbers such as #12, and versions such as v0.1 may appear.
  3. Code only for what Troy types or sees, in backticks: commands, options, file names Troy edits, and the program's output. No function, module, class, or constant names.
  4. Short sentences in everyday words. Explain in a few words any term Troy might not know, or leave it out.
  5. Every option says what Troy would see under it: "an error that asks for a word", not the name of an exception.
  6. Every recommendation says why, in one sentence.
  7. Say only what the document says. Add no judgment of your own, such as how likely a risk is when the document does not say.
Leave the record to the rest of the description, which the main session writes after the summary (Why, What, Checks): the goal as the requirements state it, the files and IDs, and the checks that ran. Remove this comment and every {{marker}}.
-->

## 给 Troy 的摘要

### 对你有什么变化

{{你会输入、看到或要做的不同之处，以及不变的地方}}

### 需要你决定的事

1. **{{要决定的事}}** {{每个方案下你会看到什么}}。推荐：{{方案}}，因为{{一句话的理由}}。

回复「全按推荐」即可全部采用推荐，或写出编号和你选的方案。

### 风险

{{可能出什么问题、可能性多大、出了问题会怎样}}

## Summary for Troy

### What changes for you

{{what you will type, see, or do differently, and what stays the same}}

### What you decide

1. **{{what is decided}}** {{what you would see under each option}}. Recommended: {{option}}, because {{one-sentence reason}}.

Reply "all as recommended" (全按推荐) to take every recommendation, or give the number and the option you want.

### Risks

{{what could go wrong for you, how likely it is, and what happens then}}
