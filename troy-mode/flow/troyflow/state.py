"""The project's state, read from git and GitHub (F07 design 5.1, D58).

Everything here comes from origin/main, the open PRs, and F07's comments on
them. The progress file is only a view of it (progress.py).
"""

from dataclasses import dataclass, field

from . import github, plugincheck, repo as git
from .repo import MAIN, Repo
from .requirements import Feature, approved, doc_version, order_problems, parse_features, \
    parse_order
from .stages import TROY_STAGES, feature_stage, merged_stages, parse_subject

INSTALL = ".troy-mode/install.toml"
REQUIREMENTS = "docs/requirements.md"
ARCHITECTURE = "docs/architecture.md"
SETUP_TITLE = "[rules] Set up troy-mode"
TROY_DOCS_TITLES = ("[docs] Add the requirements", "[docs] Add the architecture")


@dataclass
class State:
    """Everything status reads.

    Attributes:
        repo: The checkout, or None outside a git repository.
        branch: The current branch, or None.
        origin: Whether origin/main exists.
        marker: Whether the working tree has a .troy-mode folder.
        installed: Whether .troy-mode/install.toml is on origin/main.
        lang: The language pack named in the install record, or None.
        docs: Version of the requirements and the architecture on origin/main.
        checks: The comparison of the project's troy-check with the plugin's.
        approves_first: [flow] troy_approves_first on origin/main.
        features: The features table, or None.
        order: The order line's IDs, or None.
        order_problems: What breaks the order (design 5.1).
        merged: Merged stage numbers by feature.
        subjects: origin/main's subjects, newest first.
        prs: The open PRs, each with its comments read.
    """

    repo: Repo | None = None
    branch: str | None = None
    origin: bool = False
    marker: bool = False
    installed: bool = False
    lang: str | None = None
    docs: dict[str, str | None] = field(default_factory=dict)
    checks: dict = field(default_factory=lambda: {"outdated": False, "differs": []})
    approves_first: int = 3
    features: list[Feature] | None = None
    order: list[str] | None = None
    order_problems: list[str] = field(default_factory=list)
    merged: dict[str, set[int]] = field(default_factory=dict)
    subjects: list[str] = field(default_factory=list)
    prs: list[dict] = field(default_factory=list)

    def feature(self, fid: str | None) -> Feature | None:
        """Returns a feature of the table by its ID, or None."""
        return next((f for f in self.features or [] if f.id == fid), None)

    def troy_approves(self, fid: str | None) -> bool:
        """Tells whether Troy approves PR 1 and PR 2 of a feature (D61, D62)."""
        order = self.order or []
        return fid in order and order.index(fid) < self.approves_first

    def merged_by(self, title: str | None) -> str:
        """Says who merges a PR with this title: "troy" or "f07" (design 8.6)."""
        if title in TROY_DOCS_TITLES:
            return "troy"
        found = feature_stage(title or "")
        if found and found[1] in TROY_STAGES and self.troy_approves(found[0]):
            return "troy"
        return "f07"

    def feature_folder(self, fid: str) -> str | None:
        """Returns docs/features/<ID>-<slug> on origin/main, or None."""
        names = [name for name in git.folders(self.repo, MAIN, "docs/features")
                 if name.startswith(fid + "-")]
        return f"docs/features/{names[0]}" if names else None


def _read_install(state: State) -> None:
    """Reads whether setup and the language step merged on origin/main."""
    import tomllib  # noqa: PLC0415  (only needed for a set-up project)

    text = git.read(state.repo, MAIN, INSTALL)
    state.installed = text is not None
    try:
        record = tomllib.loads(text or "")
    except tomllib.TOMLDecodeError:
        record = {}
    lang = record.get("lang", {})
    state.lang = lang.get("name") if isinstance(lang, dict) else None


def _read_requirements(state: State) -> None:
    """Reads the documents, the features, and the order from origin/main."""
    text = git.read(state.repo, MAIN, REQUIREMENTS)
    state.docs = {REQUIREMENTS: doc_version(text),
                  ARCHITECTURE: doc_version(git.read(state.repo, MAIN, ARCHITECTURE))}
    if text is None:
        return
    state.features = parse_features(text)
    state.order = parse_order(text)
    state.order_problems = order_problems(state.features, state.order)


def _read_prs(state: State) -> None:
    """Reads the open PRs and their comments through gh."""
    for pr in github.open_prs(state.repo):
        number = int(pr.get("number", 0))
        pr["notes"] = github.read_comments(github.comments(state.repo, number))
        state.prs.append(pr)


def read_state(path: str | None) -> State:
    """Reads the project's state (design 5.1).

    Args:
        path: The --repo folder, or None for the current folder.

    Returns:
        The state. Outside a repository, or without origin/main, most of it
        is empty, and gh is not called.

    Raises:
        FlowError: A git or gh command failed, or the config on origin/main is invalid.
    """
    state = State(repo=git.find_repo(path))
    if state.repo is None:
        return state
    state.branch = git.branch(state.repo)
    state.marker = (state.repo.root / ".troy-mode").is_dir()
    state.origin = git.commit_of(state.repo, MAIN) is not None
    if not state.origin:
        return state
    _read_install(state)
    state.approves_first = git.config_at(state.repo, MAIN).troy_approves_first
    state.subjects = git.subjects(state.repo, MAIN)
    state.merged = merged_stages(state.subjects)
    _read_requirements(state)
    if state.installed:
        state.checks = plugincheck.compare(state.repo)
    _read_prs(state)
    return state


def pr_entry(state: State, pr: dict) -> dict:
    """Builds one open_prs entry of the report."""
    parsed = parse_subject(str(pr.get("title", "")))
    notes: github.Comments = pr["notes"]
    found = feature_stage(str(pr.get("title", "")))
    return {
        "number": int(pr.get("number", 0)), "title": pr.get("title"),
        "branch": pr.get("headRefName"), "url": pr.get("url"),
        "kind": parsed.kind if parsed else None, "item": parsed.id if parsed else None,
        "stage": found[1] if found else None, "merged_by": state.merged_by(pr.get("title")),
        "reviews": notes.reviews, "rounds": notes.rounds, "attempts": notes.attempts,
        "troy_comments": notes.troy, "waiting_for_troy": notes.waiting,
        "escalated": notes.escalated,
    }


def feature_entry(state: State, feature: Feature) -> dict:
    """Builds one features entry of the report."""
    merged = sorted(state.merged.get(feature.id, set()))
    return {"id": feature.id, "name": feature.name, "hard": feature.hard, "soft": feature.soft,
            "version": feature.version, "status": feature.status, "merged": merged,
            "accepted": 6 in merged, "troy_approves": state.troy_approves(feature.id)}


def next_feature(state: State) -> str | None:
    """Returns the first feature in the order without an accept commit, or None."""
    return next((f for f in state.order or [] if 6 not in state.merged.get(f, set())), None)


def is_approved(state: State, path: str) -> bool:
    """Tells whether a document on origin/main has version 1.0 or higher."""
    return approved(state.docs.get(path))
