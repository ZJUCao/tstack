<!-- template: The body of a version's device-test checklist (F15 design 6.2). troy-mode's engine renders it in code through `troy_flow.py issues` once the release test passes, and the main session posts it; nobody fills this file in. It holds both languages, Chinese first, with the English part folded. Each scenario Troy runs is copied from the version test plan (sections 2 and 3) and its mirror; the plan stays the source. Troy ticks the boxes; troy-mode never ticks one. Ticking every box, the last one included, accepts the version. A patch release keeps its scenario list in the second marker line. -->
<!-- troy-mode: device-test {{tag}} -->
[<!-- troy-mode: scenarios {{ID}},{{ID}} -->]
**在你的设备上测试 {{tag}}** · 第 {{run}} 轮 · 要测的提交：{{commit}}
发布 PR：#{{PR}} · [更新记录]({{url}}) · [版本测试方案]({{url}})
功能：{{F02 统计行数（状态）；…}}

测完一项、结果和预期一样，就勾上它。哪一项不对，就不勾，写一条评论说明。全部通过后，勾最后一项。

- [ ] **{{scenario-id}} {{中文场景}}**
  设备：{{设备}}。
  步骤：{{步骤}}
  预期：{{预期结果}}
- [ ] **我接受 {{tag}}。**

<details><summary>English</summary>

**Test {{tag}} on your devices** · run {{run}} · commit to test: {{commit}}
Release PR: #{{PR}} · [changelog]({{url}}) · [version test plan]({{url}})
Features: {{F02 Count lines (status); ...}}

When a scenario works as expected, tick it. If one does not, leave it unticked and write a comment. When all pass, tick the last box.

{{scenario-id}} {{scenario}}
Device: {{devices}}. Steps: {{steps}} Expected: {{expected result}}

</details>
