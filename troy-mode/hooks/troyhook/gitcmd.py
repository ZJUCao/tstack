"""git commands: the read-only list for subagents and the guards (design 7.2, 8.2)."""

import re

from .lexer import Word
from .paths import inside, to_native
from .scopes import MAIN
from .shell import SimpleCommand
from .verdict import RULE_6, Refusal

SCRATCH_HINT = ("A scratch repository in the temp folder or the scratchpad, named by a literal "
                "path or by a variable set earlier in the same command, for example to "
                "`mktemp -d`, may run any git command but push.")

_ABSOLUTE = re.compile(r"^(?:[/\\~]|[A-Za-z]:[/\\])")

ALWAYS = frozenset({
    "status", "diff", "log", "show", "blame", "grep", "rev-parse", "rev-list", "ls-files",
    "ls-tree", "cat-file", "merge-base", "describe", "shortlog", "for-each-ref", "show-ref",
    "name-rev", "check-ignore", "check-attr", "var", "diff-tree", "diff-index", "diff-files",
    "count-objects", "archive", "fetch", "ls-remote", "version", "help",
})
_GIT_GLOBAL_VALUE = frozenset({"--namespace", "--super-prefix", "--attr-source"})
_COMMIT_LONG_VALUE = frozenset({"--message", "--file", "--author", "--date", "--reuse-message",
                                "--reedit-message", "--fixup", "--squash", "--template",
                                "--cleanup", "--trailer", "--pathspec-from-file"})
_NO_VERIFY_SUBS = {
    "push": ("o", frozenset({"--repo", "--receive-pack", "--exec", "--push-option"})),
    "merge": ("mFsX", frozenset({"--message", "--file", "--strategy", "--strategy-option",
                                 "--into-name", "--cleanup"})),
    "rebase": ("sXx", frozenset({"--onto", "--strategy", "--strategy-option", "--exec"})),
    "am": ("", frozenset({"--directory", "--exclude", "--include", "--patch-format"})),
}


class GitCall:
    """A git command line, read up to and including its subcommand.

    Attributes:
        sub: The subcommand, or None for "git" alone or "git --version".
        args: The words after the subcommand.
        chdirs: The "-C" folders in order (None when a "-C" has no folder).
        dirs: ("git-dir" or "work-tree", folder) pairs from those options.
        config_keys: The lower-case names set with "-c" or "--config-env".
    """

    __slots__ = ("sub", "args", "chdirs", "dirs", "config_keys")

    def __init__(self, sub: str | None, args: list[str], chdirs: list, dirs: list,
                 config_keys: list[str]):
        """Stores the parts of the command."""
        self.sub, self.args, self.chdirs, self.dirs = sub, args, chdirs, dirs
        self.config_keys = config_keys


def parse_git(words: list[Word]) -> GitCall:
    """Reads git's global options and finds the subcommand (design 7.2)."""
    chdirs, dirs, keys, i = [], [], [], 0
    while i < len(words):
        value = words[i].value
        nxt = words[i + 1] if i + 1 < len(words) else None
        if value == "-C":
            chdirs.append(nxt)
            i += 2
        elif value in ("--git-dir", "--work-tree"):
            dirs.append((value[2:], nxt))
            i += 2
        elif value in ("-c", "--config-env"):
            keys.append(nxt.value if nxt else "")
            i += 2
        elif value.startswith(("--git-dir=", "--work-tree=")):
            kind, _, folder = value[2:].partition("=")
            dirs.append((kind, Word(folder, words[i].raw, words[i].literal)))
            i += 1
        elif value.startswith("--config-env="):
            keys.append(value.split("=", 1)[1])
            i += 1
        else:
            if not value.startswith("-"):
                break
            i += 2 if value in _GIT_GLOBAL_VALUE else 1
    sub = words[i].value if i < len(words) else None
    names = [key.split("=", 1)[0].strip().lower() for key in keys]
    return GitCall(sub, [w.value for w in words[i + 1:]], chdirs, dirs, names)


def _has_flag(args: list[str], long_flag: str, short: str, short_value: str,
              short_optional: str, long_value: frozenset) -> bool:
    """Tells whether an option is given, skipping option values and paths after "--"."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            return False
        if arg == long_flag:
            return True
        if arg.startswith("--"):
            i += 2 if arg in long_value else 1
            continue
        if arg.startswith("-") and len(arg) > 1:
            for k, char in enumerate(arg[1:], start=1):
                if short and char == short:
                    return True
                if char in short_value:
                    i += 1 if k == len(arg) - 1 else 0
                    break
                if char in short_optional:
                    break
        i += 1
    return False


def _no_verify(sub: str | None, args: list[str]) -> bool:
    """Tells whether a commit, push, merge, am, or rebase skips the git hooks (8.2)."""
    if sub == "commit":
        return _has_flag(args, "--no-verify", "n", "mFCct", "Su", _COMMIT_LONG_VALUE)
    if sub in _NO_VERIFY_SUBS:
        short_value, long_value = _NO_VERIFY_SUBS[sub]
        return _has_flag(args, "--no-verify", "", short_value, "", long_value)
    return False


def _dry_run(args: list[str]) -> bool:
    """Tells whether a push is a dry run (-n or --dry-run)."""
    short_value, long_value = _NO_VERIFY_SUBS["push"]
    return _has_flag(args, "--dry-run", "n", short_value, "", long_value)


def _branch_lists(args: list[str]) -> bool:
    """Tells whether "git branch" only lists branches."""
    listing, positional, i = False, [], 0
    while i < len(args):
        arg = args[i]
        if arg in ("-l", "--list"):
            listing = True
        elif arg in ("--points-at", "--sort", "--format"):
            i += 1
        elif arg in ("--contains", "--no-contains", "--merged", "--no-merged"):
            i += 1 if i + 1 < len(args) and not args[i + 1].startswith("-") else 0
        elif arg.startswith(("--color", "--column", "--abbrev", "--sort=", "--format=",
                             "--contains=", "--no-contains=", "--merged=", "--no-merged=",
                             "--points-at=")) or arg in ("--all", "--remotes", "--verbose",
                                                         "--show-current", "--ignore-case",
                                                         "--no-column", "--no-color",
                                                         "--no-abbrev", "--quiet",
                                                         "--omit-empty"):
            pass
        elif arg.startswith("-") and not arg.startswith("--") and set(arg[1:]) <= set("arvqil"):
            listing = listing or "l" in arg
        elif arg.startswith("-"):
            return False
        else:
            positional.append(arg)
        i += 1
    return listing or not positional


def _tag_lists(args: list[str]) -> bool:
    """Tells whether "git tag" only lists tags."""
    listing, positional, i = False, [], 0
    while i < len(args):
        arg = args[i]
        if arg in ("-l", "--list") or re.fullmatch(r"-n\d*", arg):
            listing = True
        elif arg in ("--points-at", "--sort", "--format"):
            listing, i = True, i + 1
        elif arg in ("--contains", "--no-contains", "--merged", "--no-merged"):
            listing = True
            i += 1 if i + 1 < len(args) and not args[i + 1].startswith("-") else 0
        elif arg.startswith(("--sort=", "--format=", "--contains=", "--no-contains=",
                             "--merged=", "--no-merged=", "--points-at=", "--column",
                             "--color")) or arg in ("-i", "--ignore-case", "--no-column",
                                                    "--omit-empty", "--no-color"):
            pass
        elif arg.startswith("-"):
            return False
        else:
            positional.append(arg)
        i += 1
    return listing or not positional


_CONFIG_READ = frozenset({"--get", "--get-all", "--get-regexp", "--get-urlmatch",
                          "--get-color", "--get-colorbool", "-l", "--list"})
_CONFIG_WRITE = frozenset({"--add", "--replace-all", "--unset", "--unset-all",
                           "--rename-section", "--remove-section", "-e", "--edit"})
_CONFIG_FLAGS = frozenset({"--global", "--system", "--local", "--worktree", "--show-origin",
                           "--show-scope", "--bool", "--int", "--bool-or-int", "--path",
                           "--expiry-date", "-z", "--null", "--name-only", "--includes",
                           "--no-includes", "--fixed-value", "--all"})
_CONFIG_VALUE = frozenset({"-f", "--file", "--blob", "--type", "--default"})


def _config_reads(args: list[str]) -> bool:
    """Tells whether "git config" only reads: --get, --list, get, list, or one key."""
    positional, read, i = [], False, 0
    while i < len(args):
        arg = args[i]
        if arg in _CONFIG_WRITE:
            return False
        if arg in _CONFIG_READ:
            read = True
        elif arg in _CONFIG_VALUE:
            i += 1
        elif not (arg in _CONFIG_FLAGS or arg.startswith(("--file=", "--blob=", "--type=",
                                                          "--default="))):
            if arg.startswith("-"):
                return False
            positional.append(arg)
        i += 1
    if read or (positional and positional[0] in ("get", "list")):
        return True
    return len(positional) == 1 and positional[0] not in ("set", "unset", "edit")


def _config_sets_hooks_path(args: list[str]) -> bool:
    """Tells whether "git config" sets or unsets core.hooksPath (8.2)."""
    if _config_reads(args):
        return False
    lowered = [arg.lower() for arg in args]
    sections = {"--remove-section", "--rename-section", "remove-section", "rename-section"}
    return "core.hookspath" in lowered or (bool(sections & set(lowered)) and "core" in lowered)


def _restore_worktree_only(args: list[str]) -> bool:
    """Tells whether "git restore" touches only the working tree."""
    for arg in args:
        if arg == "--":
            break
        if arg == "--staged" or arg.startswith("--source"):
            return False
        if arg.startswith("-") and not arg.startswith("--") and set(arg[1:]) & {"S", "s"}:
            return False
    return True


LISTING = {
    "branch": _branch_lists,
    "tag": _tag_lists,
    "remote": lambda a: not [x for x in a if x not in ("-v", "--verbose")]
    or [x for x in a if x not in ("-v", "--verbose")][0] in ("get-url", "show"),
    "config": _config_reads,
    "stash": lambda a: bool(a) and a[0] in ("list", "show"),
    "worktree": lambda a: bool(a) and a[0] == "list",
    "reflog": lambda a: not a or a[0] == "show" or a[0].startswith("-"),
    "restore": _restore_worktree_only,
}


def read_only(sub: str | None, args: list[str]) -> bool:
    """Tells whether a subagent may run a git subcommand in the project (design 7.2)."""
    if sub is None or sub in ALWAYS:
        return True
    check = LISTING.get(sub)
    return bool(check and check(args))


def _locations(cmd: SimpleCommand, call: GitCall) -> list[str] | None:
    """Finds every folder a git command acts on, or None when one is not known.

    With both a git directory and a work tree named (by --git-dir and
    --work-tree, or GIT_DIR and GIT_WORK_TREE), the folder the command runs
    in does not matter. Otherwise git finds its repository from that folder.
    """
    base = cmd.cwd
    for word in call.chdirs:
        if word is None or not word.literal or base is None:
            return None
        base = to_native(word.value, base)
    named = list(call.dirs)
    for name, kind in (("GIT_DIR", "git-dir"), ("GIT_WORK_TREE", "work-tree")):
        value = cmd.assignments.get(name)
        if value is not None:
            named.append((kind, Word(value, name, not set(value) & set("$`*?["))))
    kinds = {kind for kind, _ in named}
    places = [] if kinds >= {"git-dir", "work-tree"} else [base]
    for _, word in named:
        if word is None or not word.literal or (base is None and not _absolute(word.value)):
            return None
        places.append(to_native(word.value, base or "."))
    return None if None in places else places


def locations(cmd: SimpleCommand, call: GitCall) -> list[str] | None:
    """Finds every folder a git command acts on, or None when one is not known."""
    return _locations(cmd, call)


def _absolute(path: str) -> bool:
    """Tells whether a path from a command is absolute, Git Bash forms included."""
    return bool(_ABSOLUTE.match(path))


def _is_scratch(ctx, cmd: SimpleCommand, call: GitCall) -> bool:
    """Tells whether a git command acts only on a scratch repository (design 7.2).

    A scratch repository lies in the temp folder or the scratchpad and not in
    the project, even when the project itself lies in the temp folder.
    """
    places = _locations(cmd, call)
    if not places:
        return False
    temps = ctx.temp_folders()
    for place in places:
        if inside(place, ctx.project.root) or inside(place, ctx.project.git_dir):
            return False
        if not any(inside(place, temp) for temp in temps):
            return False
    return True


def _hooks_path_set(cmd: SimpleCommand, call: GitCall) -> bool:
    """Tells whether a git command changes core.hooksPath, for one run or for good."""
    if "core.hookspath" in call.config_keys:
        return True
    if any("core.hookspath" in value.lower() for value in cmd.assignments.values()):
        return True
    return call.sub == "config" and _config_sets_hooks_path(call.args)


def check_git(ctx, cmd: SimpleCommand) -> Refusal | None:
    """Checks one git command (design 7.2 for subagents, 8.2 for every caller)."""
    call = parse_git(cmd.words[1:])
    label = f"git {call.sub}" if call.sub else "git"
    if _hooks_path_set(cmd, call):
        return Refusal("hooks-path", f"`{label}` would change core.hooksPath, which turns the "
                       "troy-mode git hooks off. Nobody but Troy changes it (F05 8.2).", label)
    if _no_verify(call.sub, call.args):
        return Refusal("no-verify", f"`{label}` with --no-verify (or `commit -n`) skips the "
                       "troy-mode git hooks, which check R19 and R21. Run it without that "
                       "option (F05 8.2).", label)
    if ctx.caller.kind != MAIN:
        if _is_scratch(ctx, cmd, call):
            if call.sub == "push":
                return Refusal("git", "`git push` is refused even from a scratch repository: "
                               f"a clone can push into the project. {RULE_6}", label)
        elif not read_only(call.sub, call.args):
            return Refusal("git", f"`{label}` changes the repository, and subagents may run "
                           f"only read-only git commands in it. {RULE_6} {SCRATCH_HINT}", label)
    if call.sub in ("commit", "merge", "push") and not (call.sub == "push"
                                                         and _dry_run(call.args)):
        off = ctx.hooks_off()
        if off:
            return Refusal("hooks-off", f"`{label}` is refused: {off}", label)
    return None
