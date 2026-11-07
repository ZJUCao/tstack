"""Setup: the files and settings that make a folder a troy-mode project (design section 4)."""

from dataclasses import dataclass, field
from pathlib import Path

from .fill import add_lines, fill_config, fill_progress, fill_rules, progress_values
from .gitops import config_get, current_branch, has_remote, is_root, ref_exists
from .install import INSTALL_PATH, Install, render
from .plan import FileAction, Plan, exists, file_hash, lf_bytes, read_project_file
from .plugin import HOOKS_DEST, Plugin, owned_sources, pack_patterns, read_source
from .rules import RULES_EN, RULES_ZH

CONFIG_PATH = ".troy-mode/config.toml"
PROGRESS_PATH = ".troy-mode/progress.md"
GITIGNORE = ".gitignore"
GITIGNORE_LINES = [PROGRESS_PATH]
SETUP_TITLE = "[rules] Set up troy-mode"


@dataclass
class SetupOptions:
    """What setup fills in.

    Attributes:
        project: The project's name, for the rules table.
        email: The commit email for R19.
        date: The date written into the files, YYYY-MM-DD.
        replace: Paths setup may overwrite although it did not write them (D48).
    """

    project: str
    email: str
    date: str
    replace: list[str] = field(default_factory=list)


def owned_files(plugin: Plugin) -> list[FileAction]:
    """Builds the files troy-init copies whole: troy-check, templates, PR template, workflow."""
    return [FileAction(path, "create", read_source(source), owned=True,
                       executable=path.startswith(HOOKS_DEST + "/"))
            for path, source in owned_sources(plugin).items()]


def _gitignore(repo: Path) -> FileAction:
    """Adds the progress file to .gitignore, creating the file when it is missing."""
    existing = read_project_file(repo, GITIGNORE)
    text, action = add_lines(None if existing is None else existing.decode("utf-8", "replace"),
                             GITIGNORE_LINES)
    return FileAction(GITIGNORE, action, None if action == "keep" else lf_bytes(text))


def setup_files(plugin: Plugin, repo: Path, options: SetupOptions) -> list[FileAction]:
    """Builds every file setup writes, without the preconditions of section 4.1.

    troy-pstack's build_sample.py uses this too, so its samples are set up
    exactly as troy-init sets up a project (design section 8).

    Args:
        plugin: The plugin to copy from.
        repo: The project's root, read for .gitignore and docs/requirements.md.
        options: The name, email, and date to fill in.

    Returns:
        One action per file, sorted by path. Every action is "create", except
        .gitignore's, which may be "append" or "keep".
    """
    actions = owned_files(plugin)
    default = plugin.text("troy-mode/checks/config.default.toml")
    config = fill_config(default, options.email, pack_patterns(plugin))
    actions.append(FileAction(CONFIG_PATH, "create", lf_bytes(config)))
    for name, dest in (("rules.md", RULES_EN), ("rules.zh-CN.md", RULES_ZH)):
        text = fill_rules(plugin.text(f"troy-mode/templates/{name}"), options.project,
                          options.date, name)
        actions.append(FileAction(dest, "create", lf_bytes(text)))
    values = progress_values(options.date, exists(repo, "docs/requirements.md"))
    progress = fill_progress(plugin.text("troy-mode/templates/progress.md"), values)
    actions.append(FileAction(PROGRESS_PATH, "create", lf_bytes(progress)))
    actions.append(_gitignore(repo))
    hashes = {a.path: file_hash(a.content or b"") for a in actions if a.owned}
    record = Install(plugin.version, plugin.commit, {"setup": options.date}, None, hashes)
    actions.append(FileAction(INSTALL_PATH, "create", lf_bytes(render(record))))
    return sorted(actions, key=lambda a: a.path)


def setup_problems(repo: Path, top: Path) -> list[str]:
    """Checks the preconditions of design section 4.1.

    Args:
        repo: The folder troy-init runs on.
        top: The root of the git repository that holds it.

    Returns:
        One message per condition that does not hold.
    """
    if not is_root(repo, top):
        return [f"{repo} is not the root of its git repository ({top}). Run troy-init there."]
    problems = []
    if not has_remote(repo, "origin"):
        problems.append("The repository has no origin remote. Create the GitHub repository "
                        "and add it as origin first (design section 7, step 1).")
    elif not ref_exists(repo, "refs/remotes/origin/main"):
        problems.append("origin/main does not exist here. Run git fetch origin, or create "
                        "main on GitHub first.")
    if current_branch(repo) == "main":
        problems.append("The current branch is main. Create the branch first: "
                        "git switch -c troy-mode/init origin/main")
    if exists(repo, ".troy-mode"):
        problems.append("This project already has .troy-mode/. Run upgrade instead.")
    return problems


def _conflicts(repo: Path, actions: list[FileAction], replace: list[str]) -> list[tuple[str, str]]:
    """Finds existing files setup would overwrite, and lets --replace ones through (D48)."""
    conflicts = []
    for item in actions:
        if item.path == GITIGNORE or item.path.startswith(".troy-mode/"):
            continue
        if not exists(repo, item.path):
            continue
        if item.path in replace:
            item.action = "replace"
        else:
            conflicts.append((item.path, "exists, and troy-init did not write it. Name it with "
                                         "--replace to overwrite it."))
    return conflicts


def _git_settings(plugin: Plugin, repo: Path, plan: Plan, wanted: str) -> None:
    """Plans core.hooksPath (design 4.5) and the commit email check (design 4.3)."""
    if plugin.has_git_hooks:
        old = config_get(repo, "core.hooksPath")
        plan.git_config["core.hooksPath"] = plan.hooks_path = HOOKS_DEST
        if old and old != HOOKS_DEST:
            plan.notes.append(f"core.hooksPath was {old}; setup sets it to {HOOKS_DEST}.")
        plan.notes.append("The git hooks are on: core.hooksPath is " + HOOKS_DEST + ".")
    else:
        plan.notes.append("This troy-pstack has no git hooks yet (F05), so core.hooksPath "
                          "stays unset.")
    configured = config_get(repo, "user.email")
    plan.email = {"wanted": wanted, "configured": configured, "matches": configured == wanted}
    if configured != wanted:
        plan.notes.append(f"git config user.email is {configured or 'unset'}, not {wanted}.")
        plan.next_steps.append(f"Set this repository's commit email: git config user.email "
                               f"{wanted}")


def _next_steps(plan: Plan, has_requirements: bool) -> None:
    """Adds the PR flow's remaining steps (design section 7) to the report."""
    plan.next_steps += [
        "Stage exactly the paths in stage, those in executable with git add --chmod=+x.",
        f"Commit once with the subject {SETUP_TITLE}, run troy_check.py pr, push the branch, "
        "and open the PR.",
        "After it merges: " + ("the architecture (Architect)." if has_requirements
                               else "the requirements (Product Manager)."),
    ]


def plan_setup(plugin: Plugin, repo: Path, top: Path, options: SetupOptions) -> Plan:
    """Plans setup without changing anything.

    Args:
        plugin: The plugin to copy from.
        repo: The folder troy-init runs on.
        top: The root of the git repository that holds it.
        options: What setup fills in.

    Returns:
        The plan. It is blocked when a precondition fails or a file conflicts.
    """
    plan = Plan("setup", plugin.version)
    plan.problems = setup_problems(repo, top)
    if plan.problems and not is_root(repo, top):
        return plan
    plan.actions = setup_files(plugin, repo, options)
    plan.conflicts = _conflicts(repo, plan.actions, options.replace)
    _git_settings(plugin, repo, plan, options.email)
    _next_steps(plan, exists(repo, "docs/requirements.md"))
    return plan
