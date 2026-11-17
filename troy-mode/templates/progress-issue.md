<!-- template: The body of a feature's progress issue (F15 design 4.2). troy-mode's engine renders it in code from the state at every sync, through `troy_flow.py issues`, and the main session posts it; nobody fills this file in. It holds both languages, Chinese first, with the English part folded. The boxes are in the Chinese part only. A line in [square brackets] appears only when it applies. Links are full URLs to files on main. No time stamp. -->
<!-- troy-mode: progress {{feature-id}} -->
**{{feature-id}} {{中文功能名}}** · {{version}} · 第 {{stage}} 步，共 6 步

等你：{{等你做的事，或“没有。”}}

- [{{x 或空格}}] 1/6 接口设计：{{#PR，已合并 / 进行中。最后一次评审或尝试}}
- [ ] 2/6 测试计划
- [ ] 3/6 模拟
- [ ] 4/6 测试
- [ ] 5/6 实现
- [ ] 6/6 验收

[状态：{{需求里的状态}}]
[附带 PR：{{#PR 标题（状态）}}]
[实际运行发现的 bug：{{#issue 标题（未解决 / 已解决）}}]
[关闭未合并的 PR：{{#PR 标题}}]

依赖：{{F02（#issue，已验收），或“没有。”}}
文档：[需求]({{url}}) · [设计]({{url}}) · [测试计划]({{url}}) · [原型]({{url}})

troy-mode 维护这段文字，改动会被替换。想对 troy-mode 说什么，请写评论。

<details><summary>English</summary>

**{{feature-id}} {{feature-name}}** · {{version}} · stage {{stage}} of 6

Waiting for you: {{what waits on Troy, or "nothing."}}

1/6 Interface design: {{#PR, merged / open. The last review or attempt}}
2/6 Test plan
3/6 Mock
4/6 Tests
5/6 Implementation
6/6 Acceptance

[Status: {{the Status cell}}]
[Side PRs: {{#PR title (state)}}]
[Real-run bugs: {{#issue title (open / closed)}}]
[Closed without merging: {{#PR title}}]

Depends on: {{F02 (#issue, accepted), or "none."}}
Documents: [requirements]({{url}}) · [design]({{url}}) · [test plan]({{url}}) · [prototype]({{url}})

troy-mode keeps this text and replaces edits to it. To reach troy-mode, write a comment.

</details>
