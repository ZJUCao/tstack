"""A refused call and the wording the git and gh refusals share."""

RULE_6 = ("Common rule 6: change nothing in git or on GitHub. The main session commits, "
          "opens PRs, and posts reviews.")


class Refusal:
    """A refused call, with what goes into the log.

    Attributes:
        rule: The log's rule name, for example "git" or "scope".
        reason: The text shown to Claude.
        subcommand: The program and subcommand words, for example "git commit".
        paths: Paths for the "scope" and "changes" rules.
    """

    __slots__ = ("rule", "reason", "subcommand", "paths")

    def __init__(self, rule: str, reason: str, subcommand: str | None = None,
                 paths: tuple = ()):
        """Stores the refusal."""
        self.rule, self.reason, self.subcommand, self.paths = rule, reason, subcommand, paths
