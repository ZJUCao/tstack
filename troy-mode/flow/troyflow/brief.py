"""The brief for one role run and the Agent call's parameters (F07 design 3.2, 6.1, 6.4, 8.7, 11).

A brief is for a feature's stage, a side PR of a feature (a test fix or a
[docs] PR), a bug, a version: its test plan and its version tests (F08
design 4 and 5.3), or a rule: AR6's proposal and the cleanup PRs (F09 design
5 and 7). --title names the PR when the state cannot: a bug PR, a
side PR, the redo of a stage after a requirement change, or a fix of a
version's tests.
"""

import re
from dataclasses import dataclass

from troycheck.titles import parse_title

from . import PLUGIN_PREFIX, checksteps, mocknotes, repo as git, rulebrief, summary, teambrief
from .errors import FlowError
from .repo import MAIN
from .requirements import FEATURE_ID, parse_features
from .rework import in_rework
from .sections import adds_no_interface
from .stages import STAGE_KINDS, STAGE_TASKS, current_stage, merged_stages, parse_subject, \
    title as stage_title
from .versions import VERSION, parse_plan, plan_path, versions_of

# Every task ID of F04 section 6, written out so that a task added later
# cannot leave a gap (F08 adds TE5; F09 adds AR6, DV5, and TE6; F12 adds TM8).
ALL_TASKS = ("PM1", "PM2", "PM3", "PM4", "PM5",
             "AR1", "AR2", "AR3", "AR4", "AR5", "AR6", "AR7",
             "IF1", "IF2", "IF3", "IF4",
             "TM1", "TM2", "TM3", "TM4", "TM5", "TM6", "TM7", "TM8",
             "DV1", "DV2", "DV3", "DV4", "DV5",
             "TE1", "TE2", "TE3", "TE4", "TE5", "TE6",
             "CR1")
# Tasks of F04 that the engine cannot brief yet, with the reason.
NOT_BUILT: dict[str, str] = {}
ROLE_OF = {"AR": "architect", "IF": "interface-designer", "TM": "test-manager",
           "DV": "developer", "TE": "test-engineer", "CR": "code-reviewer"}
ARCHITECTURE_TITLE = "[docs] Add the architecture"
BUG_ID = re.compile(r"B[1-9]\d*")

# The tasks each context outside a feature's stage allows (design 8.7 and 11.1).
ACCEPTED_TASKS = ("AR4",)
TEST_FIX_TASKS = ("TE3", "TE4", "TM2", "CR1", "AR3", "AR5")
DOCS_TASKS = ("TM1", "IF2", "AR2", "IF3", "AR3", "AR4", "AR5")
BUG_A_TASKS = ("TM5", "AR3", "AR5", "TE2", "TM2", "CR1")
BUG_TEST_TASKS = ("TE2", "TM2", "CR1", "AR3", "AR5")
BUG_FIX_TASKS = ("DV3", "CR1", "TM4", "AR3", "AR5")
BUG_TEST_FIX_TASKS = ("TE3", "TM2", "CR1", "AR3", "AR5")
BUG_DOCS_TASKS = ("AR3", "AR5")
# The tasks of a version item (F08 design 4 and 5.3): its test plan in a
# [docs] PR, and its version tests in a [vX.Y tests] PR.
VERSION_DOCS_TASKS = ("TM7",)
VERSION_TESTS_TASKS = ("TE5", "TE3", "TM2", "CR1", "TM4", "AR5")
VERSION_TESTS_TITLE = "[{version} tests] End-to-end and stress tests"
# The release test's real run (F12 design 11): TM8 rules on its mismatches.
REAL_RUN_TASKS = ("TM8",)

_SENTENCES = {
    "AR7": "check the design of {item} in {folder}/design.md against the batch plan and the "
           "running teams' designs that Input gives: when the design changes an interface or a "
           "shared document that another running feature's plan names, or touches a module "
           "outside its own plan, give the new orders in the plan's fixed form. Change no file.",
    "AR1": "write the architecture in docs/architecture.md and its mirror "
           "docs/architecture.zh-CN.md. " + summary.SENTENCE,
    "AR2": "review the interface design of {item} in {folder}/design.md and fill its section 4 "
           "in both languages. Change nothing else in the design or its mirror, not even the "
           "header or the change log.",
    "AR3": "review the new dependency that Input names, for {item}: its license, maintenance, "
           "size, security record, and the option of no dependency. Report escalate with a "
           "recommendation, because Troy decides. When Input says that Troy accepted it, add it "
           "to the architecture's dependency table with an ADR, in both languages.",
    "AR4": "list the interfaces, tests, and parts of the architecture that the requirement "
           "change in Input changes for {item}, and the earliest stage of {item} that must be "
           "redone. Write an ADR only for an architecture change.",
    "AR5": "answer the question in Input from the architecture, for {item}.",
    "IF1": "write the interface design of {item} in {folder}/design.md and its mirror. Section 4 "
           "is the Architect's: write \"Not reviewed yet.\" in each Result and Note cell of its "
           "table and in its rounds log row, so no template marker is left. " + summary.SENTENCE,
    "IF2": "revise the interface design of {item} in {folder}/design.md and its mirror with the "
           "Architect's findings in Input. " + summary.SENTENCE,
    "IF3": "answer the Test Manager's question in Input from the design of {item}.",
    "IF4": "rule on the code that Input names, which the design of {item} does not describe: "
           "say whether the design missed it, and the design update it needs, or the Developer "
           "overreached, so the code is deleted. Change no file.",
    "TM1": "write the test plan of {item} in {folder}/test-plan.md and its mirror. "
           + summary.SENTENCE,
    "TM2": "review the tests of {item} against its test plan.",
    "TM3": "classify each part of {item}'s code that the coverage report leaves uncovered "
           "(Input) with the coverage gap table in your instructions, and name who fixes it. "
           "Never order tests aimed at uncovered lines. Change no file.",
    "TM4": "rule on the disputed test in Input: is the test or the code of {item} wrong? Change "
           "no file.",
    "TM5": "triage the bug report in Input: a bug, for which the Test Engineer writes a "
           "reproduction test, or a misunderstood requirement, which goes to the Product Manager "
           "as a change. Name the features it touches. Change no file.",
    "TM6": "approve or reject the written reason for the coverage exclusion in Input (R11). "
           "Change no file.",
    "TM8": "rule on each mismatch of the real run in Input, for {item}: give its kind (bug, "
           "prototype, requirement, later <feature ID>, setup, or console), the prototype, the "
           "section, the command, and the reason, one line per mismatch. Read the prototypes and "
           "run files that Input names, and the designs of their features. A mismatch is a "
           "prototype change only when a design that Troy approved chose that output; a design "
           "that only the Architect approved makes it a requirement question. Change no file.",
    "DV1": "write the mock of {item}'s interfaces.",
    "DV2": "implement {item} so that its tests pass.",
    "DV3": "fix bug {item} so that its reproduction test and every other test that must pass "
           "pass, without changing a test.",
    "DV4": "delete the code of {item} that the ruling in Input names, and nothing else.",
    "TE1": "write the tests of {item}'s test plan.",
    "TE2": "write a test named with {item} that reproduces the bug in Input and fails on the "
           "current code for the reported reason.",
    "TE3": "change only what the Test Manager's ruling in Input names, in the tests of {item}, "
           "and give the reason in your report.",
    "TE4": "write tests for the cases that the Test Manager added to the test plan of {item} "
           "(Input names them), as in TE1.",
    "TE5": "write the version tests of {item} in version-tests/: one test for each scenario of "
           "{plan} that Claude runs, and one for each performance and stress case that Claude "
           "runs. Each test's own name starts with its scenario ID, for example "
           "test_{under}_s01_<what it checks> in Python or TEST(Version, {upper}_S01_<What>) in "
           "C/C++. Test through the project's external interfaces, as a user would. Run them "
           "against the code on origin/main. A test that fails there stays as written: list it "
           "in your report with the scenario's expected result and what happened, and never "
           "bend a test to pass.",
    "TM7": "write the test plan of {item} in {plan} and its mirror from the version-test-plan "
           "template, for the features {features}: a scenario for every user flow of those "
           "features, from the requirements' user flows, prototypes, and version plan, and "
           "performance and stress cases from the requirements' targets. In the Run by column, "
           "say who runs each scenario: Claude, as an automated version test, or Troy, by hand "
           "on a device that only Troy has, such as a phone. Claude's scenarios run only in the "
           "release test on Troy's PC, never in CI, so each must run there: a scenario that "
           "needs another platform goes to Troy on a device Troy has, or is left out with the "
           "reason under the table. When the plan exists, update it to these features.",
    "CR1": "review the PR {title}.",
}
# A bug has no test plan: its tests are checked against the bug report.
_BUG_SENTENCES = {
    "TM2": "review the reproduction tests of {item} against the bug report in Input: each test's "
           "name starts with {item}, and each fails on the current code for the reported reason "
           "(R09, R15).",
}
# A version's tests are checked against the version test plan (F08 design 5.3).
_VERSION_SENTENCES = {
    "AR7": "plan the batch of {item}'s features that Input lists: for each, the modules it will "
           "touch, by their names in the architecture's module table, the external interfaces it "
           "adds or changes, and the shared documents it needs changed; order two features that "
           "change the same interface. Give the plan in Summary as one fenced block in the plan's "
           "fixed form. Change no file.",
    "TM2": "review the version tests of {item} against {plan}: every scenario that Claude runs "
           "has a test whose name starts with its ID, no test lies outside the plan, each test "
           "checks the scenario's expected result, and a test that fails, fails because the "
           "code differs from the plan, not because the test is wrong. When a scenario no "
           "longer matches the requirements, say so: the plan goes back to TM7 first.",
}
# A [docs] side PR asks the authors of documents for an addition, not a first draft.
_DOCS_SENTENCES = {
    "TM1": "add the cases in Input to the test plan of {item} in {folder}/test-plan.md and its "
           "mirror.",
    "IF2": "update the interface design of {item} in {folder}/design.md and its mirror as Input "
           "says.",
}


@dataclass
class Target:
    """What a brief is for, from --item and --title.

    Attributes:
        problems: What stops the brief before the task is looked at.
        allowed: The tasks this context allows.
        why: The problem when the task is not allowed.
        stage: The feature's stage for the report, or None.
        title: The PR title, or None.
        feature: The feature's row, or None for a bug, a version, or a rule.
        side: "test-fix" or "docs" for a side PR, else None.
        version: The version of a version item, else None.
        rule: The context of a rule item, else None.
    """

    problems: list[str]
    allowed: tuple[str, ...] = ()
    why: str = ""
    stage: int | None = None
    title: str | None = None
    feature: object = None
    side: str | None = None
    version: str | None = None
    rule: rulebrief.RuleContext | None = None


def _stop(message: str) -> Target:
    """A target that stops the brief with one problem."""
    return Target([message])


def check_task(task: str, item: str | None) -> None:
    """Checks the options a brief needs, before anything is read.

    Raises:
        FlowError: The task is no task of F04, or --item is missing or not wanted.
    """
    if task not in ALL_TASKS:
        raise FlowError(f"{task} is not a task ID of the F04 design, section 6")
    if task == "AR1" and item is not None:
        raise FlowError("AR1 writes the architecture and takes no --item")
    if task != "AR1" and item is None:
        raise FlowError(f"{task} needs --item <feature, bug, version, or rule ID>")


def parse_option_title(text: str | None):
    """Parses --title.

    Raises:
        FlowError: The text is not a troy-mode PR title.
    """
    if text is None:
        return None
    parsed = parse_title(text)
    if parsed is None:
        raise FlowError(f"--title {text!r} is not a troy-mode PR title (F02 design 4)")
    return parsed


def slug(name: str) -> str:
    """Makes a folder slug from a feature name: lower case words joined by hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def feature_folder(repo, item: str, name: str) -> str:
    """Finds the feature's folder at HEAD, or names the one its design will create."""
    names = [n for n in git.folders(repo, "HEAD", "docs/features") if n.startswith(item + "-")]
    return f"docs/features/{names[0]}" if names else f"docs/features/{item}-{slug(name)}"


def _skips_mock(repo, item: str, merged: set[int]) -> bool:
    """Tells whether the feature's design on origin/main adds no interface (D65)."""
    if 2 not in merged or 3 in merged:
        return False
    names = [n for n in git.folders(repo, MAIN, "docs/features") if n.startswith(item + "-")]
    return bool(names) and adds_no_interface(
        git.read(repo, MAIN, f"docs/features/{names[0]}/design.md"))


def _redo_target(task: str, item: str, parsed, title: str, feature, subjects: list[str],
                 merged: set[int], stage: int | None) -> Target:
    """The target for a feature stage --title: the current stage, or a redo in rework."""
    number = int(parsed.stage[0])
    if parsed.id != item:
        return _stop(f"--title {title!r} names {parsed.id}, not {item}.")
    if parsed.summary != feature.name:
        return _stop(f"--title {title!r} does not end with {item}'s name, {feature.name!r}.")
    if stage is None:
        return _stop(f"{item} is accepted: all six stages merged on origin/main.")
    if number != stage and not (number < stage and in_rework(feature, subjects, merged)):
        return _stop(f"Stage {number} is not {item}'s current stage ({stage}), and {item} is not "
                     "in rework after a requirement change.")
    return Target([], STAGE_TASKS[number], f"{task} does not belong to stage {number} of {item}.",
                  number, title, feature)


def _feature_target(repo, task: str, item: str, parsed, title: str | None, features,
                    subjects: list[str], merged_all: dict) -> Target:
    """The target for a feature item: its stage, a redo, or a side PR."""
    feature = next((f for f in features or [] if f.id == item), None)
    if feature is None:
        return _stop(f"{item} is not in the features table of docs/requirements.md on "
                     "origin/main.")
    merged = merged_all.get(item, set())
    stage = current_stage(merged, _skips_mock(repo, item, merged))
    if parsed is None and stage is None:
        return Target([], ACCEPTED_TASKS, f"{item} is accepted: all six stages merged on "
                                          "origin/main.", None, None, feature)
    if parsed is None:
        own = None if task == "AR4" else stage_title(item, stage, feature.name)
        return Target([], STAGE_TASKS[stage], f"{task} does not belong to stage {stage} of "
                                              f"{item}, its current stage.", stage, own, feature)
    if parsed.kind in STAGE_KINDS:
        return _redo_target(task, item, parsed, title, feature, subjects, merged, stage)
    if parsed.kind == "test-fix" and parsed.id == item:
        if 4 not in merged:
            return _stop(f"{item}'s tests stage has not merged, so it has no tests to fix.")
        return Target([], TEST_FIX_TASKS, f"{task} does not belong to a test fix PR.", stage,
                      title, feature, "test-fix")
    if parsed.kind == "docs":
        return Target([], DOCS_TASKS, f"{task} does not belong to a [docs] side PR.", stage,
                      title, feature, "docs")
    return _stop(f"--title {title!r} is not a title for {item}'s work.")


def _bug_target(item: str, task: str, parsed, title: str | None, subjects: list[str]) -> Target:
    """The target for a bug item: step A (PR A), step B (PR B), or a side PR (design 11.1)."""
    titles = [p for p in map(parse_subject, subjects) if p and p.id == item]
    if any(p.kind == "fix" for p in titles):
        return _stop(f"{item} is fixed: [{item} B/B fix] merged on origin/main.")
    test = next((p for p in titles if p.kind == "test"), None)
    step = "B" if test else "A"
    why = f"{task} does not belong to step {step} of bug {item}."
    if parsed is None and test:
        return Target([], BUG_FIX_TASKS, why, None, f"[{item} B/B fix] {test.summary}")
    if parsed is None:
        return Target([], BUG_A_TASKS, why)
    if parsed.kind == "docs":
        return Target([], BUG_DOCS_TASKS, why, None, title, side="docs")
    allowed = {("test", "A"): BUG_TEST_TASKS, ("fix", "B"): BUG_FIX_TASKS,
               ("test-fix", "B"): BUG_TEST_FIX_TASKS}.get((parsed.kind, step))
    if parsed.id != item or allowed is None:
        return _stop(f"--title {title!r} does not fit step {step} of bug {item}.")
    side = "test-fix" if parsed.kind == "test-fix" else None
    return Target([], allowed, why, None, title, side=side)


def _version_target(repo, task: str, version: str, parsed, title: str | None,
                    features) -> Target:
    """The target for a version item: its test plan or its version tests (F08 design 4, 5.3)."""
    if version not in versions_of(features):
        return _stop(f"{version} is not the version of any feature in the features table of "
                     "docs/requirements.md on origin/main.")
    plan = parse_plan(git.read(repo, MAIN, plan_path(version)))
    why = f"{task} does not belong to version {version}."
    if parsed is None and task in REAL_RUN_TASKS:
        return Target([], REAL_RUN_TASKS, why, None, None, version=version)
    if parsed is None and task in VERSION_DOCS_TASKS:
        verb = "Add" if plan is None else "Update"
        return Target([], VERSION_DOCS_TASKS, why, None,
                      f"[docs] {verb} the {version} test plan", version=version)
    if parsed is not None and parsed.kind == "docs":
        return Target([], VERSION_DOCS_TASKS, why, None, title, version=version)
    if parsed is not None and (parsed.kind != "version-tests" or parsed.id != version):
        return _stop(f"--title {title!r} does not fit version {version}: give a "
                     f"[{version} tests] or [docs] title.")
    if task == "TE5" and (plan is None or not plan.by("Claude")):
        return _stop(f"{plan_path(version)} is not on origin/main or has no scenario that Claude "
                     "runs, so TE5 has nothing to write; TM7 writes the plan first.")
    return Target([], VERSION_TESTS_TASKS, why, None,
                  title or VERSION_TESTS_TITLE.format(version=version), version=version)


def _plan_target(repo, item: str, title: str | None, features, subjects: list[str]) -> Target:
    """AR7's target: a version's batch to plan, or a feature's design to check (F20 3.4)."""
    if VERSION.fullmatch(item):
        if item not in versions_of(features):
            return _stop(f"{item} is not the version of any feature in the features table of "
                         "docs/requirements.md on origin/main.")
        return Target([], ("AR7",), "", None, None, version=item)
    feature = next((f for f in features or [] if f.id == item), None)
    if feature is None:
        return _stop(f"{item} is not a version or a feature in the features table of "
                     "docs/requirements.md on origin/main.")
    merged = merged_stages(subjects).get(item, set())
    stage = current_stage(merged, _skips_mock(repo, item, merged))
    own = title or (stage_title(item, stage, feature.name) if stage else None)
    return Target([], ("AR7",), "", stage, own, feature)


def _target(repo, args, parsed, features, subjects: list[str]) -> Target:
    """Finds what the brief is for and what stops it (exit 1)."""
    task, item = args.task, args.item
    if task.startswith("PM"):
        return _stop(f"{task} runs in the main session as the Product Manager; it gets no brief.")
    if task in NOT_BUILT:
        return _stop(NOT_BUILT[task])
    if task == "AR1":
        return Target([], ("AR1",), "", None, ARCHITECTURE_TITLE)
    if task == "AR7":
        return _plan_target(repo, item, args.title, features, subjects)
    if BUG_ID.fullmatch(item):
        return _bug_target(item, task, parsed, args.title, subjects)
    if VERSION.fullmatch(item):
        return _version_target(repo, task, item, parsed, args.title, features)
    if rulebrief.is_rule_item(item):
        ctx = rulebrief.context(repo, task, item, parsed, args.title)
        return Target(ctx.problems, ctx.allowed, ctx.why, None, ctx.title, rule=ctx)
    if not FEATURE_ID.fullmatch(item):
        return _stop(f"{item} is neither a feature ID, a bug ID, a version, nor a rule ID.")
    return _feature_target(repo, task, item, parsed, args.title, features, subjects,
                           merged_stages(subjects))


def _problems(task: str, target: Target, config) -> list[str]:
    """Lists what stops the brief once its target is known."""
    if target.problems:
        return target.problems
    if task not in target.allowed:
        return [target.why]
    if task in checksteps.CODE_TASKS and not config.lang.get("name"):
        return [f"{task} needs the language pack, and the config at HEAD has no [lang] name."]
    if task in checksteps.CODE_TASKS and target.title is None:
        return [f"{task} runs troy-check code on its PR: give the PR's title with --title."]
    return []


def _version_files(repo, task: str, version: str, features: list) -> list[str]:
    """The files a role on a version item reads after the architecture (F08 design 4, 5.3)."""
    ids = versions_of(features).get(version, [])
    rows = [f for f in features if f.id in ids]
    paths = [plan_path(version)]
    paths += [f"{feature_folder(repo, f.id, f.name)}/design.md" for f in rows]
    if task == "TM7":
        paths += [f"{feature_folder(repo, f.id, f.name)}/test-plan.md" for f in rows]
    if task == "TM8" or (task == "TM7" and git.files(repo, "HEAD", "docs/prototypes")):
        paths.append("docs/prototypes/")
    return paths


def _read_first(repo, task: str, item: str | None, features: list, folder: str | None,
                version: str | None = None) -> list:
    """Lists the files the role reads first (design 6.1, F08 design 4 and 5.3)."""
    paths = ["docs/rules.md", "docs/requirements.md"]
    if task == "AR1":
        return paths
    candidates = ["docs/architecture.md"]
    if version is not None:
        candidates += _version_files(repo, task, version, features)
    feature = next((f for f in features if f.id == item), None)
    if feature is not None:
        candidates += [f"{folder}/design.md", f"{folder}/test-plan.md"]
        for dep in feature.hard + feature.soft:
            candidates.append(f"{feature_folder(repo, dep, dep)}/design.md")
        if task == "TM8":
            candidates.append("docs/prototypes/")
    for path in candidates:
        if path in paths:
            continue
        if path.endswith("/") or git.exists(repo, "HEAD", path):
            paths.append(path)
    return paths


def _agent(role: str, config) -> dict:
    """The Agent call's parameters: model and effort only when [roles] at HEAD sets them."""
    agent = {"subagent_type": f"{PLUGIN_PREFIX}troy-{role}"}
    agent.update(config.roles.get(role, {}))
    return agent


def render(fields: dict) -> str:
    """Renders the brief's six fields in the format of F04 design 5.1."""
    lines = [f"Task: {fields['task']}", f"Item: {fields['item']}", "Read first:"]
    lines += [f"- {path}" for path in fields["read_first"]]
    lines += ["Input: None"] if fields["input"] is None else ["Input:", fields["input"].rstrip()]
    lines.append(f"Round: {fields['round'] if fields['round'] is not None else 'None'}")
    checks = fields["checks"]
    if checks:
        lines += ["Checks to run:"] + [f"- {c}" for c in checks]
    else:
        lines.append("Checks to run: None")
    return "\n".join(lines) + "\n"


def build(args) -> tuple[dict, int]:
    """Builds the brief for one role run.

    Args:
        args: Parsed options: task, item, title, round, input_file, and repo.

    Returns:
        The report and the exit code: 0, or 1 when a problem stops the brief.

    Raises:
        FlowError: Bad options, not a repository, or an invalid config at HEAD.
    """
    check_task(args.task, args.item)
    parsed = parse_option_title(args.title)
    text = checksteps.read_input(args.input_file)
    repo = git.need_repo(args.repo)
    config = git.config_at(repo, "HEAD")
    has_main = git.commit_of(repo, MAIN) is not None
    features = parse_features(git.read(repo, MAIN, "docs/requirements.md")) if has_main else None
    subjects = [s for _, s in git.log(repo, MAIN)] if has_main else []
    target = _target(repo, args, parsed, features, subjects)
    report = {"command": "brief", "ok": False, "notes": [], "task": args.task,
              "role": ROLE_OF.get(args.task[:2]), "item": args.item, "stage": target.stage}
    report["problems"] = _problems(args.task, target, config)
    if report["problems"]:
        return report, 1
    return _fill(report, args, repo, config, features, subjects, text, target), 0


def _fill(report: dict, args, repo, config, features, subjects, text, target: Target) -> dict:
    """Fills a brief that has no problem."""
    task, item, title, feature = args.task, args.item, target.title, target.feature
    folder = feature_folder(repo, item, feature.name) if feature else None
    version = target.version
    team = teambrief.team_of(repo)
    name = teambrief.folder_name(team, repo)
    checks = checksteps.steps(task, config, title or "", subjects, name,
                              report["notes"], version_tests=version is not None)
    if team:
        checks = teambrief.checks(team, config, checks)
    read_first = (rulebrief.read_first(repo, task, target.rule) if target.rule
                  else _read_first(repo, task, item, features or [], folder, version))
    report.update(ok=True, title=title, agent=_agent(report["role"], config),
                  read_first=read_first, input=text, round=args.round, checks=checks)
    sentences = dict(_SENTENCES)
    if item and BUG_ID.fullmatch(item) and target.side is None:
        sentences.update(_BUG_SENTENCES)
    if target.side == "docs":
        sentences.update(_DOCS_SENTENCES)
    values = {"item": item, "folder": folder, "title": title}
    if target.rule:
        sentences.update(rulebrief.sentences(target.rule))
        values.update(run=checksteps.run_prefix(config, name, report["notes"]),
                      baseline=", ".join(target.rule.files) or "the config and dependency files")
    if version is not None:
        sentences.update(_VERSION_SENTENCES)
        under = version.replace(".", "_")
        values.update(plan=plan_path(version), under=under, upper=under.upper(),
                      features=", ".join(versions_of(features).get(version, [])))
    sentence = sentences[task].format(**values)
    if team:
        sentence += " " + teambrief.sentence(team)
        report["team"] = {"id": team.id, "worktree": team.root}
    stage = target.stage if feature is not None and target.side is None else None
    notes = mocknotes.text(task, stage, config.lang.get("name"))
    if notes:
        sentence += " " + notes
    if task in checksteps.CODE_TASKS:
        sentence += " " + checksteps.PLATFORM_SKIP
    item_text = f"{item}, {title}" if item and title else (item or title)
    shown = [teambrief.absolute(team, p) if team else p for p in report["read_first"]]
    shown = [s if p != "docs/requirements.md" or (feature is None and version is None)
             else f"{s} (the {item} rows and the version plan)" if version
             else f"{s} (the {item} row in section 4)"
             for p, s in zip(report["read_first"], shown)]
    report["prompt"] = render({"task": f"{task}, {sentence}", "item": item_text,
                               "read_first": shown, "input": text, "round": args.round,
                               "checks": checks})
    return report
