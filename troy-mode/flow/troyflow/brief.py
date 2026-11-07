"""The brief for one role run and the Agent call's parameters (F07 design 3.2 and 6.1)."""

import re

from . import checksteps, repo as git
from .errors import FlowError
from .repo import MAIN
from .requirements import parse_features
from .stages import STAGE_TASKS, current_stage, merged_stages, title as stage_title

# Every task ID of F04 section 6, and the ones part 1 builds (design 14.4).
ALL_TASKS = (tuple(f"PM{n}" for n in range(1, 6)) + tuple(f"AR{n}" for n in range(1, 6))
             + tuple(f"IF{n}" for n in range(1, 5)) + tuple(f"TM{n}" for n in range(1, 8))
             + tuple(f"DV{n}" for n in range(1, 5)) + tuple(f"TE{n}" for n in range(1, 5))
             + ("CR1",))
PART1 = ("AR1", "AR2", "AR5", "IF1", "IF2", "IF3", "TM1", "TM2", "DV1", "DV2", "TE1", "CR1")
ROLE_OF = {"AR": "architect", "IF": "interface-designer", "TM": "test-manager",
           "DV": "developer", "TE": "test-engineer", "CR": "code-reviewer"}
ARCHITECTURE_TITLE = "[docs] Add the architecture"

_SENTENCES = {
    "AR1": "write the architecture in docs/architecture.md and its mirror "
           "docs/architecture.zh-CN.md.",
    "AR2": "review the interface design of {item} in {folder}/design.md and fill its section 4 "
           "in both languages. Change nothing else in the design or its mirror, not even the "
           "header or the change log.",
    "AR5": "answer the question in Input from the architecture, for {item}.",
    "IF1": "write the interface design of {item} in {folder}/design.md and its mirror. Section 4 "
           "is the Architect's: write \"Not reviewed yet.\" in each Result and Note cell of its "
           "table and in its rounds log row, so no template marker is left.",
    "IF2": "revise the interface design of {item} in {folder}/design.md and its mirror with the "
           "Architect's findings in Input.",
    "IF3": "answer the Test Manager's question in Input from the design of {item}.",
    "TM1": "write the test plan of {item} in {folder}/test-plan.md and its mirror.",
    "TM2": "review the tests of {item} against its test plan.",
    "DV1": "write the mock of {item}'s interfaces.",
    "DV2": "implement {item} so that its tests pass.",
    "TE1": "write the tests of {item}'s test plan.",
    "CR1": "review the PR {title}.",
}


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
        raise FlowError(f"{task} needs --item <feature ID>")


def slug(name: str) -> str:
    """Makes a folder slug from a feature name: lower case words joined by hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def feature_folder(repo, item: str, name: str) -> str:
    """Finds the feature's folder at HEAD, or names the one its design will create."""
    names = [n for n in git.folders(repo, "HEAD", "docs/features") if n.startswith(item + "-")]
    return f"docs/features/{names[0]}" if names else f"docs/features/{item}-{slug(name)}"


def _read_first(repo, task: str, item: str | None, features: list, folder: str | None) -> list:
    """Lists the files the role reads first (design 6.1)."""
    paths = ["docs/rules.md", "docs/requirements.md"]
    if task == "AR1":
        return paths
    candidates = ["docs/architecture.md", f"{folder}/design.md", f"{folder}/test-plan.md"]
    feature = next(f for f in features if f.id == item)
    for dep in feature.hard + feature.soft:
        candidates.append(f"{feature_folder(repo, dep, dep)}/design.md")
    for path in candidates:
        if path not in paths and git.exists(repo, "HEAD", path):
            paths.append(path)
    return paths


def _problems(task: str, item: str | None, features, stage: int | None, config) -> list[str]:
    """Finds what stops this brief (exit 1)."""
    if task.startswith("PM"):
        return [f"{task} runs in the main session as the Product Manager; it gets no brief."]
    if task not in PART1:
        return [f"{task} belongs to F07 part 2 (side PRs, bug fixes, and requirement changes) "
                "and is not built yet."]
    if task == "AR1":
        return []
    if features is None or not any(f.id == item for f in features):
        return [f"{item} is not in the features table of docs/requirements.md on origin/main."]
    if stage is None:
        return [f"{item} is accepted: all six stages merged on origin/main."]
    if task not in STAGE_TASKS[stage]:
        return [f"{task} does not belong to stage {stage} of {item}, its current stage."]
    if task in checksteps.CODE_TASKS and not config.lang.get("name"):
        return [f"{task} needs the language pack, and the config at HEAD has no [lang] name."]
    return []


def _agent(role: str, config) -> dict:
    """The Agent call's parameters: model and effort only when [roles] at HEAD sets them."""
    agent = {"subagent_type": f"troy-pstack:troy-{role}"}
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
        args: Parsed options: task, item, round, input_file, and repo.

    Returns:
        The report and the exit code: 0, or 1 when a problem stops the brief.

    Raises:
        FlowError: Bad options, not a repository, or an invalid config at HEAD.
    """
    check_task(args.task, args.item)
    text = checksteps.read_input(args.input_file)
    repo = git.need_repo(args.repo)
    config = git.config_at(repo, "HEAD")
    has_main = git.commit_of(repo, MAIN) is not None
    features = parse_features(git.read(repo, MAIN, "docs/requirements.md")) if has_main else None
    subjects = git.subjects(repo, MAIN) if has_main else []
    merged = merged_stages(subjects).get(args.item or "", set())
    stage = current_stage(merged) if args.item else None
    report = {"command": "brief", "ok": False, "notes": [], "task": args.task,
              "role": ROLE_OF.get(args.task[:2]), "item": args.item, "stage": stage}
    report["problems"] = _problems(args.task, args.item, features, stage, config)
    if report["problems"]:
        return report, 1
    return _fill(report, args, repo, config, features, subjects, text), 0


def _fill(report: dict, args, repo, config, features, subjects, text) -> dict:
    """Fills a brief that has no problem."""
    task, item, stage = args.task, args.item, report["stage"]
    feature = next((f for f in features or [] if f.id == item), None)
    title = stage_title(item, stage, feature.name) if feature else ARCHITECTURE_TITLE
    folder = feature_folder(repo, item, feature.name) if feature else None
    checks = checksteps.steps(task, config, title, subjects, repo.root.name, report["notes"])
    report.update(ok=True, title=title, agent=_agent(report["role"], config),
                  read_first=_read_first(repo, task, item, features or [], folder),
                  input=text, round=args.round, checks=checks)
    sentence = _SENTENCES[task].format(item=item, folder=folder, title=title)
    item_text = f"{item}, {title}" if item else title
    shown = [p if p != "docs/requirements.md" or not item
             else f"{p} (the {item} row in section 4)" for p in report["read_first"]]
    report["prompt"] = render({"task": f"{task}, {sentence}", "item": item_text,
                               "read_first": shown, "input": text, "round": args.round,
                               "checks": checks})
    return report
