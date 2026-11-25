"""The fixed mock-note text in the DV1, DV2, and CR1 briefs (F07 design 6.4, tstack #63).

The text goes on the Task line of a feature's stage PR only: DV1 and CR1 at
PR 3, DV2 and CR1 at PR 5. It is chosen by the config's ``[lang] name``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Sentences:
    """A language pack's fixed mock notes (design 6.4, D205).

    Attributes:
        stub: The note of a function or method whose body only raises or throws.
        constructor: The note of a class that writes its own constructor.
        generated: The notes of a class whose constructor the language
            generates: when it leaves out the checks, and when it also keeps
            values that the design changes. Empty for C/C++.
        verb: "raises" or "throws".
        example: The example of one sentence for a body that the design gives.
    """

    stub: str
    constructor: str
    generated: tuple[str, ...]
    verb: str
    example: str


PYTHON = Sentences(
    stub="The mock raises ``NotImplementedError``.",
    constructor="The mock's constructor raises ``NotImplementedError``.",
    generated=("The mock leaves out the constructor's checks.",
               "The mock keeps the values as given and leaves out the constructor's checks."),
    verb="raises",
    example="The mock reads no file, writes nothing, raises nothing, and gives 0.",
)
CPP = Sentences(
    stub="The mock throws ``troy::NotImplemented``.",
    constructor="The mock's constructor throws ``troy::NotImplemented``.",
    generated=(),
    verb="throws",
    example="The mock reads no file, writes nothing, throws nothing, and returns 0.",
)

_OPEN = ("Where the mock does less than a doc comment says, add the mock's note as a paragraph of "
         "its own, after the description and before Args, Attributes, Returns, and Raises.")
_CLOSE = ('A note never points elsewhere: no "these", "this", "above", or "below". The '
          "description and the sections describe the implementation as the design gives it, for "
          'example "The constructor checks its values, as Raises gives them.", so that PR 5 has '
          "only the notes to delete.")
_CHECK = ("Check the mock's notes. Every stub, and every class whose constructor does less in the "
          "mock than in the design, has one, as a paragraph of its own after the description. "
          "Each is one of these sentences, word for word: ")
_ANY_BODY = "one sentence that says all that a body given by the design does"

DV2 = ('Delete every paragraph of the feature\'s doc comments that starts with "The mock". Then '
       "check each doc comment of the code you write or change against that code, also the "
       "sentences you did not change. Fix each sentence that is not true of that code. What the "
       "code does includes what the functions it calls do, in any file. A sentence is not true "
       "when it names a call, a file access, or an exception that the code does not make. A full "
       'list, claimed with words such as "only", "every", or "besides", is also not true when it '
       "leaves out one that the code makes. Change nothing else in those doc comments.")
CR1_PR5 = ('Check that no paragraph of the feature\'s doc comments starts with "The mock", and that '
           "every other change to those doc comments makes them true of the code.")


def sentences(lang: str | None) -> Sentences:
    """The pack's sentences: C/C++ for ``cpp``, Python otherwise."""
    return CPP if lang == "cpp" else PYTHON


def dv1(lang: str | None) -> str:
    """DV1's text at PR 3 for the pack."""
    s = sentences(lang)
    parts = [f"`{s.stub}` for a function or method whose body only {s.verb}",
             f"`{s.constructor}` in the doc comment of a class that writes its own constructor, "
             "besides the constructor's own note"]
    if s.generated:
        checks, keeps = s.generated
        parts.append(f"`{checks}` for a class whose constructor Python generates, such as a "
                     "dataclass's, when the design has that constructor check its arguments, or "
                     f"`{keeps}` when it also changes them, for example by sorting")
    body = (f"and, for a body that the design itself gives the mock, one sentence that says all it "
            f"does, such as `{s.example}`")
    if s.generated:
        rest = ("Every other body only raises, a constructor that the class writes too, and a "
                "generated constructor gets no `__post_init__`.")
    else:
        rest = f"Every other body only {s.verb}, a constructor's too."
    listed = "; ".join(parts) + "; " + body
    return f"{_OPEN} Use these sentences word for word: {listed} {rest} {_CLOSE}"


def cr1(stage: int | None, lang: str | None) -> str | None:
    """CR1's text at PR 3 or PR 5 for the pack, or None at any other stage."""
    if stage == 5:
        return CR1_PR5
    if stage != 3:
        return None
    s = sentences(lang)
    parts = [f"`{s.stub}` for a body that only {s.verb}",
             f"`{s.constructor}` for a class that writes its own constructor"]
    if s.generated:
        checks, keeps = s.generated
        parts.append(f"`{checks}`, or `{keeps}` when the constructor also changes them, for a "
                     "class whose constructor Python generates")
    listed = "; ".join(parts) + f"; or {_ANY_BODY}"
    return f"{_CHECK}{listed}. No other sentence says what only the mock does."


def text(task: str, stage: int | None, lang: str | None) -> str | None:
    """The mock-note text for a task in a feature's stage PR, or None.

    Args:
        task: The task ID.
        stage: The stage of the feature's stage PR, or None for any other PR.
        lang: The config's ``[lang] name``.

    Returns:
        DV1's text at PR 3, DV2's at PR 5, CR1's at PR 3 or PR 5, else None.
    """
    if task == "DV1" and stage == 3:
        return dv1(lang)
    if task == "DV2" and stage == 5:
        return DV2
    if task == "CR1":
        return cr1(stage, lang)
    return None
