"""The release state and its next actions (F08 design 3.2, 3.3, 4, 5, 6, and 7).

The state stays in git and on GitHub (F07 D58): the features' versions and the
version test plans on origin/main, the release commits "[docs] Release
vX.Y.Z", the open release PR and F08's comments on it, GitHub's releases, and
the open bug issues.
"""

from . import checksteps, github
from . import repo as git
from .nextentry import make
from .repo import MAIN
from .stages import feature_stage, parse_subject, plain
from .state import State
from .versions import is_patch, parse_tag, plan_path, release_tag, version_key

RECORD_PREFIX = "[docs] Record Troy's acceptance of "
TESTS_TITLE = "[{version} tests] End-to-end and stress tests"
CODE_STAGES = (3, 4, 5, 6)


def release_commits(state: State) -> list[tuple[int, str, str]]:
    """Lists origin/main's release commits, newest first: log index, commit ID, and tag."""
    found = []
    for index, (sha, subject) in enumerate(state.log):
        tag = release_tag(plain(subject))
        if tag and parse_tag(tag):
            found.append((index, sha, tag))
    return found


def released_tags(state: State, version: str) -> list[str]:
    """Tags of a version with a release commit on origin/main, oldest first, each once."""
    tags = [c[2] for c in reversed(release_commits(state)) if parse_tag(c[2])[0] == version]
    return list(dict.fromkeys(tags))


def feature_version(state: State, fid: str) -> str | None:
    """Returns the version of a feature, or None."""
    return next((v for v, ids in state.versions.items() if fid in ids), None)


def later_code(state: State, version: str, newer_than: int | None) -> list[str]:
    """Lists the code subjects of later versions' features newer than a log index, oldest first.

    Args:
        state: The project's state.
        version: The version whose later versions count.
        newer_than: Log index of a commit (newest first); None counts every commit.
    """
    subjects = state.subjects if newer_than is None else state.subjects[:newer_than]
    found = []
    for subject in reversed(subjects):
        stage = feature_stage(subject)
        if not stage or stage[1] not in CODE_STAGES:
            continue
        other = feature_version(state, stage[0])
        if other and version_key(other) > version_key(version):
            found.append(plain(subject))
    return found


def fixes_since(state: State, newer_than: int) -> list[str]:
    """Lists the bug IDs of fix subjects newer than a log index, oldest first."""
    found = []
    for subject in reversed(state.subjects[:newer_than]):
        parsed = _bug_fix(subject)
        if parsed and parsed not in found:
            found.append(parsed)
    return found


def _bug_fix(subject: str) -> str | None:
    """Returns the bug ID of a "[B12 B/B fix]" subject, or None."""
    parsed = parse_subject(subject)
    if parsed and parsed.kind == "fix" and (parsed.id or "").startswith("B"):
        return parsed.id
    return None


def patch_info(state: State, version: str) -> dict | None:
    """The next patch of a released version (D75), or None when it has no release."""
    tags = released_tags(state, version)
    if not tags:
        return None
    index = min(c[0] for c in release_commits(state) if parse_tag(c[2])[0] == version)
    patch = max(parse_tag(t)[1] for t in tags) + 1
    fixes = fixes_since(state, index)
    blocked = later_code(state, version, index)
    return {"tag": f"{version}.{patch}", "fixes": fixes, "blocked_by": blocked,
            "allowed": bool(fixes) and not blocked}


def plan_matches(state: State, version: str) -> bool:
    """Tells whether the version's plan on origin/main lists exactly its features (D70)."""
    plan = state.plans.get(version)
    return plan is not None and set(plan.features) == set(state.versions.get(version, []))


def accepted(state: State, version: str) -> bool:
    """Tells whether every feature of a version has its accept stage merged."""
    return all(6 in state.merged.get(f, set()) for f in state.versions.get(version, []))


def version_entries(state: State) -> list[dict]:
    """Builds the report's versions list (interface note 3.1)."""
    entries = []
    for version, ids in state.versions.items():
        plan = state.plans.get(version)
        entries.append({
            "version": version, "features": list(ids), "accepted": accepted(state, version),
            "plan": plan_path(version) if plan is not None else None,
            "plan_features": list(plan.features) if plan is not None else None,
            "plan_matches": plan_matches(state, version),
            "released": released_tags(state, version), "patch": patch_info(state, version)})
    return entries


def open_release_prs(state: State) -> list[dict]:
    """The open PRs titled "[docs] Release vX.Y.Z", by number."""
    return [pr for pr in state.prs if release_tag(plain(str(pr.get("title") or "")))]


def unreleased_version(state: State) -> str | None:
    """The earliest version without a release commit for its first tag vX.Y.0."""
    have = {c[2] for c in release_commits(state)}
    return next((v for v in state.versions if f"{v}.0" not in have), None)


def target(state: State) -> tuple[str, dict | None] | None:
    """The tag the release state is about, and its open release PR, or None (rule 10)."""
    prs = open_release_prs(state)
    if prs:
        return release_tag(plain(str(prs[0].get("title")))), prs[0]
    version = unreleased_version(state)
    return (f"{version}.0", None) if version else None


def _bugs(state: State) -> list[dict]:
    """The open bug issues, read once through gh."""
    if state.open_bugs is None:
        state.open_bugs = github.open_bugs(state.repo)
    return state.open_bugs


def _release_problems(state: State, tag: str, pr: dict | None, bugs: list[dict],
                      deferred: list[int]) -> list[str]:
    """The ready checks of F08 design 5.2, as sentences."""
    version, patch = parse_tag(tag)[0], is_patch(tag)
    problems = []
    if not patch:
        problems += [f"{fid} is not accepted: its [{fid} 6/6 accept] commit is not on "
                     "origin/main." for fid in state.versions.get(version, [])
                     if 6 not in state.merged.get(fid, set())]
    for other in state.prs:
        if not parse_subject(str(other.get("title") or "")):
            continue
        if pr is None or other.get("number") != pr.get("number"):
            problems.append(f"PR #{other.get('number')} {other.get('title')} is open; it goes "
                            "first.")
    problems += [f"Issue #{b['number']} {b['title']} is an open bug: fix it through the bug "
                 "flow, or Troy defers it." for b in bugs if b["number"] not in deferred]
    if patch:
        own = [c for c in release_commits(state) if parse_tag(c[2])[0] == version]
        since = min(c[0] for c in own) if own else None
    else:
        commits = release_commits(state)
        since = commits[0][0] if commits else None
    problems += [f"{s} merged since the previous release, so the tag would hold a feature "
                 f"{version} does not include." for s in later_code(state, version, since)]
    if not patch and not plan_matches(state, version):
        problems.append(f"{plan_path(version)} is missing or does not list the features of "
                        f"{version}: the Test Manager writes it (TM7).")
    if state.checks.get("outdated"):
        problems.append("The project's troy-mode files are older than the plugin's: run "
                        "troy-init's upgrade first.")
    if patch and since is not None and not fixes_since(state, since):
        newest = released_tags(state, version)
        problems.append(f"No bug fix has merged since {newest[-1] if newest else version}.")
    return problems


def release_entry(state: State) -> dict | None:
    """Builds the report's release object (interface note 3.3), or None."""
    if not state.versions:
        return None
    found = target(state)
    if found is None:
        return None
    tag, pr = found
    version = parse_tag(tag)[0]
    plan = state.plans.get(version)
    notes = pr["notes"] if pr else None
    is_accepted = accepted(state, version)
    bugs = _bugs(state) if is_accepted or pr is not None else []
    deferred = list(notes.deferred) if notes else []
    entry = {
        "version": version, "tag": tag, "patch": is_patch(tag),
        "features": list(state.versions.get(version, [])), "accepted": is_accepted,
        "plan": plan_path(version) if plan is not None else None,
        "plan_features": list(plan.features) if plan is not None else None,
        "plan_matches": plan_matches(state, version),
        "claude_scenarios": [s.id for s in plan.by("Claude")] if plan else [],
        "troy_scenarios": [s.id for s in plan.by("Troy")] if plan else [],
        "tests_merged": tests_merged(state, version),
        "pr": int(pr.get("number", 0)) if pr else None,
        "runs": list(notes.runs) if notes else [], "deferred": deferred,
        "open_bugs": bugs, "checks": [],
        "problems": _release_problems(state, tag, pr, bugs, deferred)}
    return entry


def tests_merged(state: State, version: str) -> bool:
    """Tells whether a "[vX.Y tests]" commit of the version is on origin/main."""
    for subject in state.subjects:
        parsed = parse_subject(subject)
        if parsed and parsed.kind == "version-tests" and parsed.id == version:
            return True
    return False


def release_checks(state: State, title: str, notes: list[str]) -> list[str]:
    """The release test's commands: the pack's steps, troy-check code, and the release command."""
    config = git.config_at(state.repo, MAIN)
    return checksteps.release_test_steps(config, title, state.subjects, state.repo.root.name,
                                         notes)


# --------------------------------------------------------------------------- next actions


def record_rule(state: State) -> dict | None:
    """record-acceptance: a release merged without Troy's acceptance recorded (design 5.7)."""
    for _, _, tag in reversed(release_commits(state)):
        version = parse_tag(tag)[0]
        plan = state.plans.get(version)
        if plan is None or tag in plan.accepted_tags:
            continue
        if any(plain(s) == RECORD_PREFIX + tag for s in state.subjects):
            continue
        return make("record-acceptance", item=version, tag=tag, task="PM4",
                    title=RECORD_PREFIX + tag, branch=f"troy-mode/record-{tag}",
                    merged_by="f07", doc=plan_path(version))
    return None


def tag_rule(state: State) -> dict | None:
    """tag: a release commit on origin/main without its GitHub release (design 5.7, D73)."""
    commits = release_commits(state)
    if not commits:
        return None
    if state.gh_releases is None:
        state.gh_releases = github.release_tags(state.repo)
    for _, sha, tag in reversed(commits):
        if tag not in state.gh_releases:
            return make("tag", item=parse_tag(tag)[0], tag=tag, commit=sha)
    return None


def retro_rule(state: State, notes: list[str]) -> dict | None:
    """retro: the newest version released without a Retrospective comment (design 7)."""
    commits = [c for c in release_commits(state) if not is_patch(c[2])]
    if not commits or state.gh_releases is None or commits[0][2] not in state.gh_releases:
        return None
    tag = commits[0][2]
    title = f"[docs] Release {tag}"
    pr = next((p for p in github.merged_prs(state.repo)
               if plain(str(p.get("title") or "")) == title), None)
    if pr is None:
        notes.append(f"No merged PR titled {title} was found, so the retrospective of {tag} "
                     "cannot be checked.")
        return None
    number = int(pr.get("number", 0))
    found = github.read_comments(github.comments(state.repo, number))
    if tag in found.retrospectives:
        return None
    return make("retro", item=parse_tag(tag)[0], tag=tag, pr=number, title=pr.get("title"))


def plan_rule(state: State, fid: str | None) -> dict | None:
    """version-test-plan: a feature's version has no plan, or a plan for other features (D70)."""
    version = feature_version(state, fid) if fid else None
    if version is None or plan_matches(state, version):
        return None
    return plan_entry(state, version)


def plan_entry(state: State, version: str) -> dict:
    """The next entry that asks the Test Manager for a version's test plan (TM7)."""
    verb = "Add" if state.plans.get(version) is None else "Update"
    return make("version-test-plan", item=version, task="TM7",
                title=f"[docs] {verb} the {version} test plan",
                branch=f"troy-mode/{version}-test-plan", merged_by="f07", doc=plan_path(version))


def _step(state: State, tag: str, pr: dict | None) -> tuple[str, dict]:
    """The release's next step and its keys (design 3.3)."""
    version = parse_tag(tag)[0]
    if pr is None:
        plan = state.plans.get(version)
        if not is_patch(tag) and plan and plan.by("Claude") and not tests_merged(state, version):
            return "version-tests", {"task": "TE5", "title": TESTS_TITLE.format(version=version),
                                     "branch": f"troy-mode/{version}-tests"}
        return "release-pr", {"task": "PM4", "title": f"[docs] Release {tag}",
                              "branch": f"troy-mode/release-{tag}"}
    keys = {"pr": int(pr.get("number", 0)), "title": pr.get("title"),
            "branch": pr.get("headRefName")}
    notes = pr["notes"]
    last = notes.runs[-1] if notes.runs else None
    if last is None:
        return "release-test", keys
    if last["by"] == "claude" and last["result"] == "passed":
        return "troy-test", keys
    if last["by"] == "troy" and last["result"] == "accepted":
        return "accept", dict(keys, task="PM4")
    left = [b for b in _bugs(state) if b["number"] not in notes.deferred]
    if left:
        return "bugs", dict(keys, item=f"B{left[0]['number']}", task="TM5")
    return "release-test", keys


def release_rule(state: State, release_pr_first: bool) -> dict | None:
    """release, or version-test-plan at release time (rule 10 of the interface note).

    Args:
        state: The project's state.
        release_pr_first: The first open troy-mode PR is a release PR.
    """
    if not state.versions:
        return None
    found = target(state)
    if found is None:
        return None
    tag, pr = found
    if pr is not None and not release_pr_first:
        return None
    version = parse_tag(tag)[0]
    if not is_patch(tag) and not accepted(state, version):
        return None
    if not is_patch(tag) and pr is None and not plan_matches(state, version):
        return plan_entry(state, version)
    step, keys = _step(state, tag, pr)
    values = {"item": version, "tag": tag, "merged_by": "f07", "step": step}
    values.update(keys)
    return make("release", **values)
