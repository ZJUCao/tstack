"""The security review's check of a PR's diff, and a release's review branch (tstack #75).

CR1's brief says whether to run `/security-review`, from four signs in the
lines that the PR's diff adds: a dependency, a subprocess call, network
access, and credential handling (F07 design 6.5, F04 D280). The lists are
chosen by the config's ``[lang] name``, as mocknotes.py chooses its text.
CR2 reviews a release on a local branch whose one commit puts origin/main's
files on the previous release commit (F08 design 5.9, F04 D283).
"""

import re
from dataclasses import dataclass

from troycheck.classify import classify

from . import repo as git
from .repo import MAIN
from .stages import plain
from .versions import TAG, parse_tag, release_tag

KINDS = ("dependency", "subprocess", "network", "credential")
_WORDS = {"dependency": "a dependency change", "subprocess": "a subprocess call",
          "network": "network access", "credential": "credential handling"}
# Places shown for each kind before "and <n> more".
SHOWN = 3
NOT_NEEDED = ("troy-mode's check finds no dependency, subprocess call, network access, or "
              "credential handling that the diff adds, so `/security-review` is not needed, "
              "unless you see one of those four that the check missed.")
REVIEW_BRANCH = re.compile(rf"troy-mode/({TAG.pattern})-security")

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SECRET_WORDS = ("password", "passwd", "passphrase", "credential", "secret", "api_key",
                 "apikey", "access_token", "auth_token", "private_key")
_PACKAGE_LINE = re.compile(r"\b(find_package|FetchContent_Declare|ExternalProject_Add|"
                           r"CPMAddPackage|pkg_check_modules)\s*\(", re.IGNORECASE)

# Python (F07 design 6.5).
_PY_IMPORT = re.compile(r"^\s*import\s+(.+)$")
_PY_FROM = re.compile(r"^\s*from\s+(\.*[A-Za-z_][\w.]*|\.+)\s+import\s+(.+)$")
_PY_MODULES = {
    "subprocess": {"subprocess", "pty"},
    "network": {"socket", "ssl", "http", "urllib", "urllib3", "ftplib", "smtplib", "poplib",
                "imaplib", "xmlrpc", "socketserver", "webbrowser", "requests", "httpx",
                "aiohttp", "websockets", "grpc", "paramiko"},
    "credential": {"getpass", "keyring", "netrc", "secrets"},
}
_OS_RUN = r"(system|popen|exec\w*|spawn\w*|posix_spawn\w*)"
_PY_TEXT = {
    "subprocess": (re.compile(r"\bsubprocess\."), re.compile(rf"\bos\.{_OS_RUN}\s*\("),
                   re.compile(r"\basyncio\.create_subprocess_\w+")),
    "network": (re.compile(r"\basyncio\.(open_connection|start_server)\b"),),
}

# C and C++ (F07 design 6.5).
_INCLUDE = re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]")
_CPP_CALLS = {
    "subprocess": re.compile(r"\b(system|popen|_popen|_wpopen|execl|execle|execlp|execv|execve|"
                             r"execvp|execvpe|fork|vfork|posix_spawnp?|CreateProcess\w*|"
                             r"ShellExecute\w*|WinExec)\s*\("),
    "network": re.compile(r"\b(getaddrinfo|WSAStartup)\s*\("),
}
_CPP_HEADERS = {
    "subprocess": (("spawn.h",), ("boost/process",)),
    "network": (("sys/socket.h", "arpa/inet.h", "netdb.h", "winsock.h", "winsock2.h",
                 "ws2tcpip.h", "curl/curl.h", "asio.hpp"), ("netinet/", "boost/asio")),
}


@dataclass(frozen=True)
class Sign:
    """One sign that the diff adds.

    Attributes:
        kind: One of KINDS.
        path: The file, from the repository root.
        line: The line in the new file, or None for a dependency file.
    """

    kind: str
    path: str
    line: int | None


def _modules(text: str) -> list[str]:
    """The top-level modules a Python import line names, or [] for any other line."""
    code = text.split("#", 1)[0]
    found = _PY_FROM.match(code)
    if found:
        module = found.group(1)
        return [] if module.startswith(".") else [module.split(".")[0]]
    found = _PY_IMPORT.match(code)
    if not found:
        return []
    names = [part.strip().split()[0] for part in found.group(1).split(",") if part.strip()]
    return [name.split(".")[0] for name in names]


def _from_os(text: str) -> bool:
    """Tells whether a line imports a process call from os by name."""
    found = _PY_FROM.match(text.split("#", 1)[0])
    if not found or found.group(1) != "os":
        return False
    names = [part.strip(" ()").split()[0] for part in found.group(2).split(",") if part.strip(" ()")]
    return any(re.fullmatch(_OS_RUN, name) for name in names)


def _secret_name(text: str) -> bool:
    """Tells whether a line holds a name that speaks of a password, a secret, or a key."""
    return any(word in name.lower() for name in _NAME.findall(text) for word in _SECRET_WORDS)


def _python_kinds(text: str) -> set[str]:
    """The kinds of sign that one added Python line gives."""
    kinds = {kind for kind, names in _PY_MODULES.items() if set(_modules(text)) & names}
    kinds |= {kind for kind, patterns in _PY_TEXT.items() if any(p.search(text) for p in patterns)}
    if _from_os(text):
        kinds.add("subprocess")
    if _secret_name(text):
        kinds.add("credential")
    return kinds


def _cpp_kinds(text: str) -> set[str]:
    """The kinds of sign that one added C or C++ line gives."""
    kinds = {kind for kind, pattern in _CPP_CALLS.items() if pattern.search(text)}
    header = _INCLUDE.match(text)
    if header:
        name = header.group(1).strip().lower()
        for kind, (exact, prefixes) in _CPP_HEADERS.items():
            if name in exact or name.startswith(prefixes):
                kinds.add(kind)
    if _secret_name(text):
        kinds.add("credential")
    return kinds


PACKS = {"python": _python_kinds, "cpp": _cpp_kinds}


def _is_cmake(path: str) -> bool:
    """Tells whether a dependency file is a CMake file, which also lists the project's own files."""
    return path.rsplit("/", 1)[-1] == "CMakeLists.txt" or path.startswith("cmake/")


def _quoted(path: str) -> str:
    """Undoes git's quoting of an unusual path, and the tab after a path with spaces."""
    path = path.rstrip("\t")
    if len(path) > 1 and path.startswith('"') and path.endswith('"'):
        return path[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape") \
            .encode("latin-1").decode("utf-8", "replace")
    return path


def changes(repo) -> tuple[list[str], dict[str, list[tuple[int, str]]]]:
    """Reads the PR's diff from its merge base with origin/main to HEAD.

    Returns:
        The changed paths, deleted ones included, and each new file's added
        lines with their line numbers.

    Raises:
        FlowError: git fails, for example without origin/main.
    """
    base = git.git(repo, "merge-base", MAIN, "HEAD").strip()
    names = git.git(repo, "-c", "core.quotepath=false", "diff", "--no-ext-diff", "-M",
                    "--name-only", "-z", base, "HEAD")
    paths = [p for p in names.split("\0") if p]
    text = git.git(repo, "-c", "core.quotepath=false", "diff", "--no-ext-diff", "--no-color",
                   "-M", "-U0", base, "HEAD")
    added: dict[str, list[tuple[int, str]]] = {}
    current, number = None, 0
    for line in text.split("\n"):
        if line.startswith("+++ "):
            target = line[4:]
            if target.startswith('"b/'):
                current = _quoted('"' + target[3:])
            elif target.startswith("b/"):
                current = _quoted(target[2:])
            else:
                current = None
            continue
        if line.startswith("@@"):
            found = re.search(r"\+(\d+)", line)
            number = int(found.group(1)) if found else 0
            continue
        if current is None or line.startswith(("--- ", "diff --git", "\\")):
            continue
        if line.startswith("+"):
            added.setdefault(current, []).append((number, line[1:].rstrip("\r")))
            number += 1
    return paths, added


def find(repo, config) -> list[Sign]:
    """Finds the signs that the PR's diff adds, for the config's language pack.

    Raises:
        FlowError: git fails.
    """
    kinds_of = PACKS[config.lang.get("name")]
    paths, added = changes(repo)
    found: set[Sign] = set()
    for path in paths:
        if classify(path, config.paths) != "dependencies":
            continue
        if not _is_cmake(path) or any(_PACKAGE_LINE.search(t) for _, t in added.get(path, [])):
            found.add(Sign("dependency", path, None))
    for path, lines in added.items():
        if classify(path, config.paths) != "source":
            continue
        for number, text in lines:
            found.update(Sign(kind, path, number) for kind in kinds_of(text))
    return sorted(found, key=lambda s: (KINDS.index(s.kind), s.path, s.line or 0))


def _join(items: list[str]) -> str:
    """Joins items as "X", "X and Y", or "X, Y, and Z"."""
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _places(signs: list[Sign]) -> str:
    """The places of one kind: up to SHOWN, then how many more."""
    shown = [s.path if s.line is None else f"{s.path}:{s.line}" for s in signs]
    text = ", ".join(shown[:SHOWN])
    if len(shown) > SHOWN:
        text += f", and {len(shown) - SHOWN} more"
    return text


def sentence(repo, config) -> str:
    """CR1's sentence about `/security-review` (F07 design 6.5).

    Raises:
        FlowError: git fails.
    """
    lang = config.lang.get("name")
    if lang not in PACKS:
        return ("Run `/security-review` too, because troy-mode's check has no lists for the "
                f"language pack {lang}.")
    signs = find(repo, config)
    if not signs:
        return NOT_NEEDED
    parts = []
    for kind in KINDS:
        mine = [s for s in signs if s.kind == kind]
        if mine:
            parts.append(f"{_WORDS[kind]} ({_places(mine)})")
    return f"Run `/security-review` too, because the diff adds {_join(parts)}."


# --------------------------------------------------------------------------- the review branch


def review_base(repo) -> tuple[str, str | None]:
    """The commit a release's review starts from: the newest release commit, or the first commit.

    Returns:
        The commit ID and its tag, or None for the root commit of origin/main.

    Raises:
        FlowError: git fails, for example without origin/main.
    """
    for sha, subject in git.log(repo, MAIN):
        tag = release_tag(plain(subject))
        if tag and parse_tag(tag):
            return sha, tag
    roots = git.git(repo, "rev-list", "--max-parents=0", MAIN).split()
    return roots[-1], None


def review_branch(tag: str) -> str:
    """The name of a release's local review branch (F08 design 5.9)."""
    return f"troy-mode/{tag}-security"


def check_review_branch(repo, version: str) -> tuple[list[str], dict]:
    """Checks that HEAD is the review branch of a release of the version (F07 design 6.5).

    Returns:
        The problems, and the tag and the words for the base when there are none.

    Raises:
        FlowError: git fails.
    """
    why = ("CR2 runs only on the review branch troy-mode/<tag>-security that status gives at "
           "the release step security-review (F08 design 5.9): ")
    name = git.branch(repo)
    found = REVIEW_BRANCH.fullmatch(name or "")
    if not found or parse_tag(found.group(1))[0] != version:
        return [why + f"HEAD is on {name or 'no branch'}, not a review branch of {version}."], {}
    tag = found.group(1)
    parents = git.git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
    if len(parents) != 1:
        return [why + f"{name} must hold exactly one commit on its base."], {}
    trees = git.git(repo, "rev-parse", "HEAD^{tree}", f"{MAIN}^{{tree}}").split()
    if trees[0] != trees[1]:
        return [why + f"the files of {name} differ from origin/main's; make the branch again."], {}
    base, base_tag = review_base(repo)
    if parents[0] != base:
        return [why + f"the parent of {name} is not {base_tag or 'the first commit'} ({base})."], {}
    return [], {"tag": tag, "since": base_tag or "the first commit"}


def review_commands(repo, tag: str, base: str) -> list[str]:
    """The commands that make a release's review branch, in order (F08 design 5.9)."""
    commands = []
    if git.commit_of(repo, "refs/remotes/origin/HEAD") is None:
        commands.append("git remote set-head origin --auto")
    commands.append(f'git commit-tree "origin/main^{{tree}}" -p {base} '
                    f'-m "Security review of {tag}"')
    commands.append(f"git switch -c {review_branch(tag)} <commit>")
    return commands
