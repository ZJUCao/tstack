"""The premise attempt: an author's fourth attempt tests what the three failed ones shared
(F18 design 6, D175).

`brief --premise` adds TEXT to the Task line and the attack-the-premise card to
Read first. brief imports this module, so it is part of F16's instruction set.
"""

from pathlib import Path

# The author tasks that count attempts, whose fourth run may test the premise.
TASKS = ("IF1", "IF2", "TM1", "TM7", "DV1", "DV2", "DV3", "DV4", "DV5",
         "TE1", "TE2", "TE3", "TE4", "TE5", "TE6", "AR1")
CARD = Path(__file__).resolve().parents[3] / "skills/principle-attack-the-premise/SKILL.md"
TEXT = ("This is your fourth attempt: the three before it failed with the checks in Input. "
        "Before you change any file, write down in one sentence the premise that all three "
        "attempts shared. Test it with a check that changes no file, and name the observation "
        "that would come out differently if the premise were false. Then follow the evidence: "
        "fix the new cause when it lies inside your write scope, or report escalate when it "
        "lies outside it, such as in a check, a test you do not own, the design, or the "
        "environment. A cause in the environment, such as a variable, an installed tool, or "
        "a missing environment, is outside your write scope even when your own commands "
        "could get around it: report escalate, and do not work around it. Start your "
        "report's Summary with three lines, Premise:, Check:, and Result:, which give the "
        "premise, the check, and what it showed.")


def card() -> str:
    """The card's absolute path, in POSIX form, for Read first."""
    return CARD.as_posix()
