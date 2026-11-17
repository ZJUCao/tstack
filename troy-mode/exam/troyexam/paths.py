"""The work root and its folders (design 11.1)."""

from collections.abc import Mapping
from pathlib import Path

from . import DEFAULT_ROOT, ROOT_VARIABLE


def work_root(env: Mapping[str, str]) -> Path:
    """Returns the work root: the folder that ROOT_VARIABLE names, or DEFAULT_ROOT."""
    return Path(env.get(ROOT_VARIABLE) or DEFAULT_ROOT)


def repository_name(repository: str) -> str:
    """Returns the last part of "owner/name", or of a local folder's path, without ".git"."""
    name = repository.replace("\\", "/").rstrip("/").split("/")[-1]
    return name[:-4] if name.endswith(".git") else name


class Layout:
    """The folders of the work root.

    Attributes:
        root: The work root.
        mirrors: Bare mirrors of the start repositories.
        envs: The environments, one per start repository and lock file.
        runs: One folder per run while it runs.
        results: One folder per exam.
        cases: Each case's runs, as cases/<case ID>.tsv.
        climb: Hillclimb logs.
    """

    def __init__(self, root: Path):
        """Names the folders of root; creates none."""
        self.root = Path(root)
        self.mirrors = self.root / "mirrors"
        self.envs = self.root / "envs"
        self.runs = self.root / "runs"
        self.results = self.root / "results"
        self.cases = self.root / "cases"
        self.climb = self.root / "climb"

    def mirror(self, repository: str) -> Path:
        """Returns mirrors/<name>.git for "owner/name"."""
        return self.mirrors / f"{repository_name(repository)}.git"

    def case_log(self, case_id: str) -> Path:
        """Returns cases/<case ID>.tsv."""
        return self.cases / f"{case_id}.tsv"

    def result(self, exam_id: str) -> Path:
        """Returns results/<exam ID>."""
        return self.results / exam_id

    def climb_log(self, name: str) -> Path:
        """Returns climb/<name>/decision.tsv."""
        return self.climb / name / "decision.tsv"
