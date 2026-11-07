"""R12: English documents and their Chinese mirrors (design section 6.4)."""

import posixpath
from dataclasses import dataclass

from .context import PrContext
from .frontmatter import Header, header_problems, parse_header, structure, version_key
from .gitio import files_containing, read_blob
from .globs import matches_any
from .report import FAIL, PASS, SKIP, Detail, Result, outcome

# troy-init copies the templates here. They hold markers and share troy-doc
# IDs with the project's documents on purpose, so they are not documents.
NOT_DOCUMENTS = [".troy-mode/**"]


@dataclass
class Doc:
    """A document as it is in one commit.

    Attributes:
        path: Repository path.
        header: Its parsed header.
    """

    path: str
    header: Header

    @property
    def lang(self) -> str:
        """The document's lang field."""
        return self.header.fields.get("lang", "")

    def partner_path(self) -> str | None:
        """The path its mirror or mirror-of field points to, in the same folder."""
        key = "mirror" if self.lang == "en" else "mirror-of"
        name = self.header.fields.get(key)
        if not name:
            return None
        return posixpath.join(posixpath.dirname(self.path), name)


def load_doc(ctx: PrContext, commit: str, path: str) -> Doc | None:
    """Reads a path as a document.

    Args:
        ctx: The PR under check.
        commit: Commit to read from.
        path: Repository path.

    Returns:
        The document, or None if the file is missing, is not Markdown, lies
        under .troy-mode/, or has no troy-doc header.
    """
    if not path.endswith(".md") or matches_any(path, NOT_DOCUMENTS):
        return None
    text = read_blob(ctx.repo, commit, path)
    header = parse_header(text) if text is not None else None
    if header is None or not header.is_document:
        return None
    return Doc(path, header)


def _changed_sets(ctx: PrContext) -> tuple[set[str], list[str]]:
    """Splits changes into paths present at head and paths deleted from base."""
    present, deleted = set(), []
    for change in ctx.changes:
        if change.status == "D":
            deleted.append(change.path)
            continue
        present.add(change.path)
        if change.old_path is not None and change.status == "R":
            deleted.append(change.old_path)
    return present, deleted


def _pair_problems(doc: Doc, partner: Doc | None, partner_path: str) -> list[str]:
    """Checks that two documents point at each other and match (points 2 and 3)."""
    if partner is None:
        return [f"its mirror {partner_path} is missing or has no troy-doc header"]
    problems = [f"mirror {partner.path}: {p}" for p in header_problems(partner.header)]
    want = "zh-CN" if doc.lang == "en" else "en"
    if partner.lang != want:
        problems.append(f"mirror {partner.path} has lang {partner.lang!r}, expected {want!r}")
    if partner.partner_path() != doc.path:
        problems.append(f"mirror {partner.path} does not point back to {doc.path}")
    for key in ("troy-doc", "version"):
        if doc.header.fields.get(key) != partner.header.fields.get(key):
            problems.append(f"{key} differs from {partner.path}: "
                            f"{doc.header.fields.get(key)!r} vs {partner.header.fields.get(key)!r}")
    return problems


def _shape_problems(en: Doc, zh: Doc) -> list[str]:
    """Compares heading levels and table columns of a pair (point 6)."""
    en_heads, en_tables = structure(en.header.body)
    zh_heads, zh_tables = structure(zh.header.body)
    problems = []
    if en_heads != zh_heads:
        problems.append(f"heading levels differ from {zh.path}: {en_heads} vs {zh_heads}")
    if en_tables != zh_tables:
        problems.append(f"table columns differ from {zh.path}: {en_tables} vs {zh_tables}")
    return problems


def _version_problems(ctx: PrContext, en: Doc, present: set[str], partner: str) -> list[str]:
    """Checks the version raise and that the mirror changed too (point 4)."""
    problems = []
    if partner not in present:
        problems.append(f"changed without its mirror {partner}")
    old = load_doc(ctx, ctx.base, _old_path(ctx, en.path))
    if old is None:
        return problems
    new_v = version_key(en.header.fields.get("version", ""))
    old_v = version_key(old.header.fields.get("version", ""))
    if new_v is not None and old_v is not None and new_v <= old_v:
        problems.append(f"version {en.header.fields['version']} is not higher than "
                        f"{old.header.fields['version']} at the merge base")
    return problems


def _old_path(ctx: PrContext, path: str) -> str:
    """Returns where a changed path lived at the merge base."""
    for change in ctx.changes:
        if change.path == path and change.old_path is not None:
            return change.old_path
    return path


def _check_doc(ctx: PrContext, doc: Doc, present: set[str]) -> list[str]:
    """Runs points 1 to 4 and 6 for one changed document."""
    problems = header_problems(doc.header)
    partner_path = doc.partner_path()
    if problems or partner_path is None:
        return problems
    partner = load_doc(ctx, ctx.head, partner_path)
    if (doc.lang == "zh-CN" and partner is not None and partner_path in present
            and partner.partner_path() == doc.path):
        return []  # The English side checks this pair and reports for both.
    problems += _pair_problems(doc, partner, partner_path)
    if partner is None:
        return problems
    if doc.lang == "en":
        problems += _version_problems(ctx, doc, present, partner_path)
        problems += _shape_problems(doc, partner)
    elif partner.path not in present:
        problems += _shape_problems(partner, doc)
    return problems


def _deleted_problems(ctx: PrContext, deleted: list[str]) -> list[Detail]:
    """Checks that a deleted document's partner is gone too (point 5)."""
    details = []
    for path in deleted:
        doc = load_doc(ctx, ctx.base, path)
        partner = doc.partner_path() if doc else None
        if partner and read_blob(ctx.repo, ctx.head, partner) is not None:
            details.append(Detail(path, None, f"deleted, but its pair {partner} remains"))
    return details


def _duplicate_ids(ctx: PrContext) -> list[Detail]:
    """Finds English documents at head that share a troy-doc ID."""
    seen: dict[str, str] = {}
    details = []
    for path in sorted(files_containing(ctx.repo, ctx.head, r"^troy-doc:", "*.md")):
        doc = load_doc(ctx, ctx.head, path)
        if doc is None or doc.lang != "en":
            continue
        doc_id = doc.header.fields["troy-doc"]
        if doc_id in seen:
            details.append(Detail(path, None, f"troy-doc {doc_id!r} is also used by {seen[doc_id]}"))
        else:
            seen[doc_id] = path
    return details


def check_r12(ctx: PrContext) -> Result:
    """Checks changed documents against their mirrors (R12).

    Args:
        ctx: The PR under check.

    Returns:
        SKIP when no document changed, FAIL with one detail per problem, and
        PASS otherwise.
    """
    present, deleted = _changed_sets(ctx)
    docs = [d for d in (load_doc(ctx, ctx.head, p) for p in sorted(present)) if d]
    deleted_docs = [p for p in deleted if load_doc(ctx, ctx.base, p)]
    if not docs and not deleted_docs:
        return Result("R12", SKIP, "No documents changed.")
    fails = []
    for doc in docs:
        fails += [Detail(doc.path, None, p) for p in _check_doc(ctx, doc, present)]
    fails += _deleted_problems(ctx, deleted_docs)
    if docs:
        fails += _duplicate_ids(ctx)
    count = len(docs) + len(deleted_docs)
    noun = "document" if count == 1 else "documents"
    if outcome(fails, []) == FAIL:
        return Result("R12", FAIL, f"{len(fails)} problems in {count} changed {noun}.", fails)
    return Result("R12", PASS, f"{count} changed {noun} match their mirrors.")
