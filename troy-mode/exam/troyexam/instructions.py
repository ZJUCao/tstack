"""The instruction set: the files that make up the roles' instructions, and their hash (design 9.1).

The runner, `affected`, and the CI check `troy-mode/dev/check_exam.py` all read
the set from here. A tree is a folder on disk or one commit of a git
repository; both give the same hash for the same content, CRLF read as LF.
"""

import ast
import hashlib
import re
import subprocess
from pathlib import Path

from .errors import ExamError

FIXED = ("agents/troy-*.md", "troy-mode/roles/common.md", "troy-mode/templates/**",
         "troy-mode/exam/cases/**", "troy-mode/exam/troyexam/**")
BRIEF = "troy-mode/flow/troyflow/brief.py"
FLOW_PACKAGE = "troy-mode/flow/troyflow"
SKILL = "skills/troy-mode/SKILL.md"
SKILL_SECTIONS = ("Running a role", "The summary for Troy")
_NAMERS = ("agents/troy-*.md", "troy-mode/roles/common.md")
_SKILL_NAME = re.compile(r"skills/([A-Za-z0-9_.-]+)/")
_SKIP_PARTS = ("__pycache__", ".git")
# A version of the hash's layout, so that a later change of layout changes every hash.
_LAYOUT = b"tstack instruction set 1\n"


def glob_match(path: str, pattern: str) -> bool:
    """Matches a POSIX path against a pattern: * within one folder name, ** across folders."""
    regex, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            regex += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            regex += ".*"
            i += 2
        elif pattern[i] == "*":
            regex += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(pattern[i])
            i += 1
    return re.fullmatch(regex, path) is not None


class FolderTree:
    """A checkout or a plugin copy on disk.

    Attributes:
        root: The folder.
    """

    def __init__(self, root: Path):
        """Reads files under root."""
        self.root = Path(root)

    def files(self) -> list[str]:
        """Every file under the root, as POSIX paths, without caches and .git."""
        found = []
        for path in self.root.rglob("*"):
            rel = path.relative_to(self.root).as_posix()
            if any(part in _SKIP_PARTS for part in rel.split("/")) or rel.endswith(".pyc"):
                continue
            if path.is_file():
                found.append(rel)
        return sorted(found)

    def read(self, path: str) -> bytes | None:
        """The file's bytes, or None when it is missing."""
        full = self.root / path
        return full.read_bytes() if full.is_file() else None


class GitTree:
    """One commit of a git repository.

    Attributes:
        repo: The repository.
        ref: The commit, branch, or tag.
    """

    def __init__(self, repo: Path, ref: str):
        """Reads ref of repo; nothing is checked out."""
        self.repo, self.ref = Path(repo), ref
        self._files: list[str] | None = None
        self._cache: dict[str, bytes | None] = {}

    def _git(self, *args: str, data: bytes | None = None) -> bytes:
        """Runs git in the repository; ExamError when it fails."""
        proc = subprocess.run(["git", "-C", str(self.repo), *args], input=data,
                              capture_output=True)
        if proc.returncode:
            raise ExamError(f"git {' '.join(args)}: {proc.stderr.decode(errors='replace').strip()}")
        return proc.stdout

    def files(self) -> list[str]:
        """Every file of the commit."""
        if self._files is None:
            out = self._git("ls-tree", "-r", "--name-only", "-z", self.ref)
            self._files = sorted(p for p in out.decode("utf-8").split("\0") if p)
        return list(self._files)

    def read(self, path: str) -> bytes | None:
        """The file's bytes at the commit, or None when it is missing."""
        if path not in self._cache:
            self.read_many([path])
        return self._cache[path]

    def read_many(self, paths: list[str]) -> None:
        """Reads several files at once into the cache."""
        wanted = [p for p in paths if p not in self._cache]
        if not wanted:
            return
        known = set(self.files())
        present = [p for p in wanted if p in known]
        for p in wanted:
            if p not in known:
                self._cache[p] = None
        if not present:
            return
        data = "".join(f"{self.ref}:{p}\n" for p in present).encode("utf-8")
        out = self._git("cat-file", "--batch", data=data)
        pos = 0
        for p in present:
            end = out.index(b"\n", pos)
            header = out[pos:end].split()
            if len(header) < 3 or header[1] == b"missing":
                self._cache[p] = None
                pos = end + 1
                continue
            size = int(header[2])
            self._cache[p] = out[end + 1:end + 1 + size]
            pos = end + 1 + size + 1


def _text(data: bytes | None) -> str:
    """Decodes a file as UTF-8 with CRLF read as LF."""
    return (data or b"").replace(b"\r\n", b"\n").decode("utf-8", errors="replace")


def _module_imports(source: str) -> set[str]:
    """The troyflow modules that one module's relative imports name."""
    found = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return found
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module:
                found.add(node.module.split(".")[0])
            else:
                found.update(alias.name for alias in node.names)
    return found


def brief_modules(tree) -> list[str]:
    """brief.py, troyflow's __init__.py, and every troyflow module that brief.py imports, at any depth."""
    files = set(tree.files())
    init = f"{FLOW_PACKAGE}/__init__.py"
    found = {BRIEF} if BRIEF in files else set()
    if init in files:
        found.add(init)
    todo = [BRIEF] if BRIEF in files else []
    while todo:
        for name in _module_imports(_text(tree.read(todo.pop()))):
            path = f"{FLOW_PACKAGE}/{name}.py"
            if path in files and path not in found:
                found.add(path)
                todo.append(path)
    return sorted(found)


def skills_in(*texts: str) -> list[str]:
    """The skills/<name>/ folders that the texts name, other than troy-mode's, sorted once each."""
    names = set()
    for text in texts:
        names.update(_SKILL_NAME.findall(text))
    names.discard("troy-mode")
    return sorted(f"skills/{name}/" for name in names)


def named_skills(tree) -> list[str]:
    """The skills/<name>/ folders that an agent file, common.md, or a module of the brief names.

    The brief's modules name the cards it adds to Read first, such as the premise card and
    the card table's (F17 design 5, D163).
    """
    paths = [p for p in tree.files() if any(glob_match(p, pattern) for pattern in _NAMERS)]
    paths += brief_modules(tree)
    return skills_in(*(_text(tree.read(path)) for path in paths))


def instruction_files(tree) -> list[str]:
    """Every file of the instruction set but SKILL.md, whose two sections count instead."""
    files = tree.files()
    skills = named_skills(tree)
    found = {p for p in files if any(glob_match(p, pattern) for pattern in FIXED)}
    found.update(brief_modules(tree))
    found.update(p for p in files if any(p.startswith(folder) for folder in skills))
    found.discard(SKILL)
    return sorted(found)


def skill_sections(text: str) -> dict[str, str]:
    """The two role sections of SKILL.md, each up to the next level-2 heading; "" when missing."""
    text = text.replace("\r\n", "\n")
    parts = re.split(r"(?m)^(?=## )", text)
    sections = {}
    for name in SKILL_SECTIONS:
        match = [p for p in parts if p.split("\n", 1)[0].strip() == f"## {name}"]
        sections[name] = match[0] if match else ""
    return sections


def instruction_hash(tree) -> str:
    """The SHA-256 of the list, every instruction file, and SKILL.md's two role sections."""
    files = instruction_files(tree)
    if isinstance(tree, GitTree):
        tree.read_many(files + [SKILL])
    digest = hashlib.sha256(_LAYOUT)
    for line in (*FIXED, BRIEF, SKILL, *SKILL_SECTIONS):
        digest.update(line.encode("utf-8") + b"\n")
    for path in files:
        digest.update(b"\0file\0" + path.encode("utf-8") + b"\0")
        digest.update((tree.read(path) or b"").replace(b"\r\n", b"\n"))
    sections = skill_sections(_text(tree.read(SKILL)))
    for name in SKILL_SECTIONS:
        digest.update(b"\0section\0" + name.encode("utf-8") + b"\0")
        digest.update(sections[name].encode("utf-8"))
    return digest.hexdigest()


def short_hash(full: str) -> str:
    """The first 12 characters of a hash, as the PR section shows it."""
    return full[:12]
