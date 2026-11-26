"""The text of troy-mode's issues: fixed words in both languages and the two bodies (F15 design
4.2, 6.2, 8.2, and 8.3).

The templates progress-issue.md and device-test-issue.md give these shapes;
this module renders them. Bodies hold the Chinese part first and the English
part folded below it, the boxes in the Chinese part only, and no time stamp.
"""

from dataclasses import dataclass, field

STAGES = {1: ("接口设计", "Interface design"), 2: ("测试计划", "Test plan"), 3: ("模拟", "Mock"),
          4: ("测试", "Tests"), 5: ("实现", "Implementation"), 6: ("验收", "Acceptance")}
ROLES = {"Architect": "架构师", "Interface Designer": "接口设计师", "Test Manager": "测试经理",
         "Developer": "开发工程师", "Test Engineer": "测试工程师", "Code Reviewer": "代码审查员",
         "Product Manager": "产品经理"}
RESULTS = {"approved": ("通过", "approved"), "changes-requested": ("要求修改", "changes requested"),
           "needs-answer": ("需要回答", "needs an answer"), "escalate": ("上报", "escalated")}
PR_STATES = {"OPEN": ("进行中", "open"), "MERGED": ("已合并", "merged"),
             "CLOSED": ("已关闭", "closed")}
FEATURE_STATES = {"accepted": ("已验收", "accepted"), "in progress": ("进行中", "in progress"),
                  "not started": ("未开始", "not started")}
NOTHING = ("没有。", "nothing.")
SKIPPED_MOCK = ("跳过：没有新接口", "skipped: no new interface")
PROGRESS_FOOTER = ("troy-mode 维护这段文字，改动会被替换。想对 troy-mode 说什么，请写评论。",
                   "troy-mode keeps this text and replaces edits to it. To reach troy-mode, "
                   "write a comment.")
CHECKLIST_HELP = ("测完一项、结果和预期一样，就勾上它。哪一项不对，就不勾，写一条评论说明。全部通过后，勾最后一项。",
                  "When a scenario works as expected, tick it. If one does not, leave it unticked "
                  "and write a comment. When all pass, tick the last box.")
DOC_NAMES = {"requirements": ("需求", "requirements"), "design": ("设计", "design"),
             "test-plan": ("测试计划", "test plan"), "prototype": ("原型", "prototype")}
MAX_BODY = 60_000


def link(text: str, url: str) -> str:
    """A Markdown link."""
    return f"[{text}]({url})"


def waiting_texts(kind: str, pr: int | None, text: str = "") -> tuple[str, str]:
    """What waits on Troy, in both languages (design 4.2).

    Args:
        kind: "nothing", "approve", "escalation", or "question".
        pr: The PR that waits.
        text: The escalation's trigger or the question.
    """
    if kind == "approve":
        return (f"批准 #{pr}；要决定的事在它描述的开头。",
                f"approve #{pr}; what to decide is at the top of its description.")
    if kind == "escalation":
        return f"#{pr} 上的上报：{text}。", f"the escalation on #{pr}: {text}."
    if kind == "question":
        return f"回答 #{pr} 上的问题：{text}。", f"answer the question on #{pr}: {text}."
    return NOTHING


def review_texts(heading: dict) -> tuple[str, str]:
    """The last review or attempt of an open PR, translated (design 4.2).

    Args:
        heading: {"role", "round", "result"} for a review, or {"role", "attempt"}.
    """
    role = heading["role"]
    if "attempt" in heading:
        return (f"{ROLES.get(role, role)}第 {heading['attempt']} 次尝试：失败",
                f"{role}, attempt {heading['attempt']}: failed")
    zh, en = RESULTS.get(heading["result"], (heading["result"], heading["result"]))
    return f"{ROLES.get(role, role)}第 {heading['round']} 轮：{zh}", f"{role}, round {heading['round']}: {en}"


RULINGS = {"merge": "合并", "fix": "要改", "fixed": "已改", "not fixed": "未改好"}


def ruling_texts(pr: int, ruler: str, round_: int, result: str, url: str) -> tuple[str, str]:
    """A ruled PR's line: its newest result and a link to the ruling (F18 design 5.3)."""
    return (f"裁定：#{pr} {ROLES.get(ruler, ruler)}第 {round_} 轮：{RULINGS.get(result, result)}"
            f"（{link('裁定', url)}）",
            f"Ruling: #{pr} {ruler}, round {round_}: {result} ({link('ruling', url)})")


def overturn_texts(ruling: str, done: bool) -> tuple[str, str]:
    """Troy's overturn of a ruling, being carried out or carried out (F18 design 5.3)."""
    return (f"推翻：{ruling}（{'已完成' if done else '进行中'}）",
            f"Overturn: {ruling} ({'carried out' if done else 'being carried out'})")


@dataclass
class Box:
    """One stage of a progress issue: its number, whether it is ticked, and its text after the name."""

    stage: int
    ticked: bool
    zh: str = ""
    en: str = ""


@dataclass
class ProgressFacts:
    """Everything a progress issue shows, worked out from the state (design 4.2)."""

    fid: str
    name_en: str
    name_zh: str
    version: str | None
    stage: int
    waiting: tuple[str, str]
    boxes: list[Box]
    status: tuple[str, str] | None = None
    extra: list[tuple[str, str]] = field(default_factory=list)
    deps: list[tuple[str, str]] = field(default_factory=list)
    docs: list[tuple[str, str, str]] = field(default_factory=list)


def progress_title(fid: str, name_en: str, name_zh: str | None) -> str:
    """The progress issue's title, Chinese first: "F04 把历史导出为 CSV / Export history as CSV"."""
    return f"{fid} {name_zh} / {name_en}" if name_zh and name_zh != name_en else f"{fid} {name_en}"


def _box_line(box: Box, zh: bool) -> str:
    """One stage line, with its box in Chinese and without one in English."""
    name = STAGES[box.stage][0 if zh else 1]
    detail = box.zh if zh else box.en
    sep = "：" if zh else ": "
    text = f"{box.stage}/6 {name}{sep + detail if detail else ''}"
    return f"- [{'x' if box.ticked else ' '}] {text}" if zh else text


def progress_body(facts: ProgressFacts) -> str:
    """Renders a progress issue's body (design 4.2)."""
    version = f" · {facts.version}" if facts.version else ""
    zh = [f"<!-- troy-mode: progress {facts.fid} -->",
          f"**{facts.fid} {facts.name_zh or facts.name_en}**{version} · 第 {facts.stage} 步，共 6 步", "",
          f"等你：{facts.waiting[0]}", ""]
    zh += [_box_line(box, True) for box in facts.boxes]
    en = [f"**{facts.fid} {facts.name_en}**{version} · stage {facts.stage} of 6", "",
          f"Waiting for you: {facts.waiting[1]}", ""]
    en += [_box_line(box, False) for box in facts.boxes]
    zh_more, en_more = [], []
    if facts.status:
        zh_more.append(f"状态：{facts.status[0]}")
        en_more.append(f"Status: {facts.status[1]}")
    for line_zh, line_en in facts.extra:
        zh_more.append(line_zh)
        en_more.append(line_en)
    if zh_more:
        zh += [""] + zh_more
        en += [""] + en_more
    zh += ["", "依赖：" + ("，".join(d[0] for d in facts.deps) if facts.deps else "没有。")]
    en += ["", "Depends on: " + (", ".join(d[1] for d in facts.deps) if facts.deps else "none.")]
    if facts.docs:
        zh.append("文档：" + " · ".join(link(DOC_NAMES[kind][0], url_zh)
                                       for kind, url_zh, _ in facts.docs))
        en.append("Documents: " + " · ".join(link(DOC_NAMES[kind][1], url_en)
                                             for kind, _, url_en in facts.docs))
    zh += ["", PROGRESS_FOOTER[0], "", "<details><summary>English</summary>", ""]
    en += ["", PROGRESS_FOOTER[1], "", "</details>"]
    return "\n".join(zh + en) + "\n"


@dataclass
class Scenario:
    """One scenario Troy runs, in both languages (design 6.2)."""

    id: str
    title: tuple[str, str]
    devices: tuple[str, str]
    steps: tuple[str, str]
    expected: tuple[str, str]
    ticked: bool = False


@dataclass
class ChecklistFacts:
    """Everything a checklist shows (design 6.2)."""

    tag: str
    run: int
    commit: str
    pr: int | None
    changelog: tuple[str, str]
    plan: tuple[str, str]
    features: list[tuple[str, str]]
    scenarios: list[Scenario]
    accept: bool = False
    named: list[str] | None = None
    short: bool = False
    samples: list[tuple[int, str, bool]] = field(default_factory=list)


def checklist_title(tag: str) -> str:
    """The checklist's title: "v0.1.0 在你的设备上测试 / Test v0.1.0 on your devices"."""
    return f"{tag} 在你的设备上测试 / Test {tag} on your devices"


def checklist_body(facts: ChecklistFacts) -> str:
    """Renders a checklist's body (design 6.2). With short, steps are links to the plan."""
    commit = facts.commit[:7] if facts.commit else "未知"
    pr = f"#{facts.pr}" if facts.pr else "无"
    zh = [f"<!-- troy-mode: device-test {facts.tag} -->"]
    if facts.named is not None:
        zh.append(f"<!-- troy-mode: scenarios {','.join(facts.named)} -->")
    zh += [f"**在你的设备上测试 {facts.tag}** · 第 {facts.run} 轮 · 要测的提交：{commit}",
           f"发布 PR：{pr} · {link('更新记录', facts.changelog[0])} · "
           f"{link('版本测试方案', facts.plan[0])}",
           "功能：" + "；".join(f[0] for f in facts.features), "", CHECKLIST_HELP[0], ""]
    en = [f"**Test {facts.tag} on your devices** · run {facts.run} · commit to test: "
          f"{facts.commit[:7] if facts.commit else 'unknown'}",
          f"Release PR: {'#' + str(facts.pr) if facts.pr else 'none'} · "
          f"{link('changelog', facts.changelog[1])} · {link('version test plan', facts.plan[1])}",
          "Features: " + "; ".join(f[1] for f in facts.features), "", CHECKLIST_HELP[1]]
    for scenario in facts.scenarios:
        box = "x" if scenario.ticked else " "
        steps_zh = f"见{link('版本测试方案', facts.plan[0])}" if facts.short else scenario.steps[0]
        steps_en = (f"see {link('the version test plan', facts.plan[1])}" if facts.short
                    else scenario.steps[1])
        zh += [f"- [{box}] **{scenario.id} {scenario.title[0]}**",
               f"  设备：{scenario.devices[0]}。", f"  步骤：{steps_zh}", f"  预期：{scenario.expected[0]}"]
        en += ["", f"{scenario.id} {scenario.title[1]}",
               f"Device: {scenario.devices[1]}. Steps: {steps_en} Expected: {scenario.expected[1]}"]
    for number, title, ticked in facts.samples:
        box = "x" if ticked else " "
        zh.append(f"- [{box}] **抽查 #{number} {title}**：已合并、没等你批准的抽查。"
                  "看过它的摘要就勾上；不同意就在这个功能的进度 issue 上评论。")
        en += ["", f"Spot check #{number} {title}: merged without your approval. Tick it once you "
               "have read its summary; to disagree, comment on the feature's progress issue."]
    zh += [f"- [{'x' if facts.accept else ' '}] **我接受 {facts.tag}。**", "",
           "<details><summary>English</summary>", ""]
    en += ["", "</details>"]
    return "\n".join(zh + en) + "\n"
