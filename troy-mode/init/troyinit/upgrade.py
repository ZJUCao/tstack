"""Upgrade: troy-mode's own files brought to the plugin's version (design section 6, D54)."""

import tomllib
from pathlib import Path

from .errors import InitError
from .gitops import config_get, current_branch, is_root
from .install import INSTALL_PATH, Install, parse, render
from .plan import FileAction, Plan, exists, file_hash, lf_bytes, read_project_file
from .plugin import HOOKS_DEST, Plugin, owned_sources, pack_patterns, read_source
from .rules import RULES_EN, RULES_ZH, upgrade_pair
from .setup import CONFIG_PATH

UPGRADE_TITLE = "[rules] Upgrade troy-mode to {version}"
_REPLACE_HINT = " Name it with --replace to let upgrade overwrite it."


def upgrade_problems(repo: Path, top: Path) -> list[str]:
    """Checks that the project is set up and the branch is not main.

    Args:
        repo: The folder troy-init runs on.
        top: The root of the git repository that holds it.

    Returns:
        One message per condition that does not hold.
    """
    if not is_root(repo, top):
        return [f"{repo} is not the root of its git repository ({top}). Run troy-init there."]
    problems = []
    if current_branch(repo) == "main":
        problems.append("The current branch is main. Create the branch first: "
                        "git switch -c troy-mode/upgrade-<version> origin/main")
    if not exists(repo, INSTALL_PATH):
        problems.append(f"This project is not set up: {INSTALL_PATH} is missing. "
                        "Run setup first.")
    return problems


def _changed_owned(path: str, want: bytes, current: bytes | None, recorded: str | None,
                   replace: list[str]) -> tuple[FileAction | None, str | None]:
    """Decides an owned file the plugin still has. Returns the action or a conflict."""
    executable = path.startswith(HOOKS_DEST + "/")
    if current is not None and current.replace(b"\r\n", b"\n") == want:
        return FileAction(path, "keep", owned=True, executable=executable), None
    if current is None and recorded is None:
        return FileAction(path, "create", want, owned=True, executable=executable), None
    unchanged = current is not None and recorded is not None and file_hash(current) == recorded
    if unchanged or path in replace:
        action = "create" if current is None else "replace"
        return FileAction(path, action, want, owned=True, executable=executable), None
    if current is None:
        return None, "was deleted since troy-init wrote it." + _REPLACE_HINT
    if recorded is None:
        return None, "exists, and troy-init did not write it." + _REPLACE_HINT
    return None, "was edited since troy-init wrote it." + _REPLACE_HINT


def _dropped_owned(path: str, current: bytes | None, recorded: str | None,
                   replace: list[str]) -> tuple[FileAction | None, str | None]:
    """Decides an owned file the plugin no longer has. Returns the action or a conflict."""
    if current is None:
        return None, None
    if (recorded is not None and file_hash(current) == recorded) or path in replace:
        return FileAction(path, "delete", owned=True), None
    return None, ("was edited since troy-init wrote it, and troy-pstack no longer has it. "
                  "Name it with --replace to let upgrade delete it.")


def _owned_actions(plugin: Plugin, repo: Path, install: Install, replace: list[str],
                   plan: Plan) -> dict[str, str]:
    """Plans every owned file under the hash rule. Returns the new [files] hashes."""
    wanted = {path: read_source(source) for path, source in owned_sources(plugin).items()}
    hashes = {}
    for path in sorted(set(wanted) | set(install.files)):
        current = read_project_file(repo, path)
        recorded = install.files.get(path)
        if path in wanted:
            action, conflict = _changed_owned(path, wanted[path], current, recorded, replace)
        else:
            action, conflict = _dropped_owned(path, current, recorded, replace)
        if conflict:
            plan.conflicts.append((path, conflict))
        if action:
            plan.actions.append(action)
            if path in wanted:
                hashes[path] = file_hash(wanted[path])
    return hashes


def _rules_actions(plugin: Plugin, repo: Path, date: str, plan: Plan) -> None:
    """Plans the rules table's R rows, version, and change log (design 6)."""
    en, zh = read_project_file(repo, RULES_EN), read_project_file(repo, RULES_ZH)
    if en is None or zh is None:
        plan.differences.append((RULES_EN, "The rules table or its mirror is missing, so "
                                           "its R rows were not upgraded."))
        return
    try:
        result = upgrade_pair(en.decode("utf-8"), zh.decode("utf-8"),
                              plugin.text("troy-mode/templates/rules.md"),
                              plugin.text("troy-mode/templates/rules.zh-CN.md"),
                              date, plugin.version)
    except (InitError, UnicodeDecodeError) as exc:
        plan.differences.append((RULES_EN, f"Its R rows were not upgraded: {exc}"))
        return
    if result is None:
        plan.actions += [FileAction(RULES_EN, "keep"), FileAction(RULES_ZH, "keep")]
    else:
        plan.actions += [FileAction(RULES_EN, "edit", lf_bytes(result[0])),
                         FileAction(RULES_ZH, "edit", lf_bytes(result[1]))]


def config_differences(plugin: Plugin, repo: Path) -> list[tuple[str, str]]:
    """Lists the pack patterns the project's config lacks; upgrade never edits it.

    Args:
        plugin: The plugin.
        repo: The project's root.

    Returns:
        (path, message) pairs, empty when the config has every pattern.
    """
    raw = read_project_file(repo, CONFIG_PATH)
    if raw is None:
        return [(CONFIG_PATH, "is missing.")]
    try:
        paths = tomllib.loads(raw.decode("utf-8")).get("paths", {})
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        return [(CONFIG_PATH, f"cannot be read: {exc}")]
    found = []
    for key, patterns in pack_patterns(plugin).items():
        missing = [p for p in patterns if p not in paths.get(key, [])]
        if missing:
            found.append((CONFIG_PATH, f"[paths] {key} lacks {', '.join(missing)}, which "
                                       f"troy-pstack {plugin.version} sets up."))
    return found


def _hooks_note(repo: Path, plan: Plan) -> None:
    """Says how git hooks that arrive with the upgrade get turned on."""
    arriving = any(a.action == "create" and a.path.startswith(HOOKS_DEST + "/")
                   for a in plan.actions)
    if arriving and config_get(repo, "core.hooksPath") != HOOKS_DEST:
        plan.notes.append("The git hooks arrive with this upgrade. troy-pstack's SessionStart "
                          f"hook turns them on in each clone by setting core.hooksPath to "
                          f"{HOOKS_DEST}.")


def _finish(plugin: Plugin, install: Install, hashes: dict[str, str], date: str,
            plan: Plan) -> None:
    """Adds the rewritten install record and the next steps, or says nothing changes."""
    if not plan.changed:
        plan.notes.append(f"Nothing to upgrade: troy-mode's files already match troy-pstack "
                          f"{plugin.version}.")
        return
    steps = {**install.steps, "upgrade": date}
    record = Install(plugin.version, plugin.commit, steps, install.lang, hashes)
    plan.actions.append(FileAction(INSTALL_PATH, "edit", lf_bytes(render(record))))
    title = UPGRADE_TITLE.format(version=plugin.version)
    plan.next_steps += [
        "Stage exactly the paths in stage, those in executable with git add --chmod=+x.",
        f"Commit once with the subject {title}, run troy_check.py pr, push the branch, "
        "and open the PR.",
    ]


def plan_upgrade(plugin: Plugin, repo: Path, top: Path, date: str, replace: list[str]) -> Plan:
    """Plans the upgrade without changing anything.

    Args:
        plugin: The plugin to upgrade to.
        repo: The folder troy-init runs on.
        top: The root of the git repository that holds it.
        date: The date written into the files.
        replace: Owned files upgrade may overwrite or delete although edited.

    Returns:
        The plan. It is blocked when a precondition fails or a file conflicts.

    Raises:
        InitError: The install record cannot be read, or it names a language
            pack, whose upgrade comes with F06 part 2.
    """
    plan = Plan("upgrade", plugin.version)
    plan.problems = upgrade_problems(repo, top)
    if plan.problems:
        return plan
    install = parse((read_project_file(repo, INSTALL_PATH) or b"").decode("utf-8", "replace"))
    if install.lang:
        raise InitError("this project has a language pack; upgrading it comes with F06 part 2")
    hashes = _owned_actions(plugin, repo, install, replace, plan)
    _rules_actions(plugin, repo, date, plan)
    plan.differences += config_differences(plugin, repo)
    _hooks_note(repo, plan)
    _finish(plugin, install, hashes, date, plan)
    plan.actions.sort(key=lambda a: a.path)
    return plan
