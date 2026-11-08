"""Sections of a design document, for the check after AR2 (F07 design 7, F04 D37).

The Architect writes section 4 of a design, its review, and nothing else in it.
"""

import re

_FENCE = re.compile(r"^\s*(```|~~~)")
SECTION_FOUR = "## 4."


def blocks(text: str) -> list[tuple[str, str]]:
    """Cuts a Markdown document at its level-two headings, outside code blocks.

    Args:
        text: The document.

    Returns:
        Pairs of the heading line ("" for the part before the first heading)
        and the block's whole text, in order.
    """
    result, heading, current, fenced = [], "", [], False
    for line in text.replace("\r\n", "\n").split("\n"):
        if _FENCE.match(line):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            result.append((heading, "\n".join(current)))
            heading, current = line.rstrip(), []
        current.append(line)
    result.append((heading, "\n".join(current)))
    return result


def outside_section_four(before: str | None, after: str | None) -> list[str]:
    """Lists what changed in a design outside its section 4.

    Args:
        before: The design at HEAD, or None when it is new.
        after: The design in the working tree, or None when it was deleted.

    Returns:
        One phrase per change, empty when only section 4 changed.
    """
    if before is None:
        return ["the file is new"]
    if after is None:
        return ["the file was deleted"]
    old, new = blocks(before), blocks(after)
    if [h for h, _ in old] != [h for h, _ in new]:
        return ["its headings were added, removed, renamed, or reordered"]
    changed = []
    for (heading, old_text), (_, new_text) in zip(old, new):
        if heading.startswith(SECTION_FOUR) or old_text == new_text:
            continue
        changed.append(f"the section {heading[3:]!r}" if heading else "the header and title")
    return changed


SECTION_TWO = "## 2."


def adds_no_interface(text: str | None) -> bool:
    """Tells whether a feature design's section 2 lists no interface (design 11.2, D65).

    A change to an accepted feature that only changes existing interfaces
    leaves section 2 without an interface subsection, and F07 skips its mock.

    Args:
        text: The design, or None when it does not exist.

    Returns:
        True when the design has a section 2 that holds no line starting
        "### " outside fenced code blocks; False otherwise, also when the
        design or its section 2 is missing.
    """
    if text is None:
        return False
    for heading, block in blocks(text):
        if not heading.startswith(SECTION_TWO):
            continue
        fenced = False
        for line in block.split("\n"):
            if _FENCE.match(line):
                fenced = not fenced
            elif not fenced and line.startswith("### "):
                return False
        return True
    return False
