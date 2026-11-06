"""Builders for the text of configs, PR descriptions, and documents.

These functions only produce strings and dictionaries. They never touch git.
"""

from __future__ import annotations

import json
from typing import Iterable, Mapping, Optional, Sequence

EMAIL = "troy@example.test"


def make_config(
    email: Optional[str] = EMAIL,
    paths: Optional[Mapping[str, Sequence[str]]] = None,
    limits: Optional[Mapping[str, int]] = None,
    mode: Optional[str] = None,
    extra: str = "",
) -> str:
    """Builds the text of a ``.troy-mode/config.toml`` file.

    Args:
        email: ``commit_email`` value, or None to leave identity out.
        paths: Mapping of ``[paths]`` keys to pattern lists.
        limits: Mapping of ``[limits]`` keys to integers.
        mode: ``[attribution]`` mode, or None to leave it out.
        extra: Raw TOML appended at the end.

    Returns:
        The TOML text.
    """
    parts = []
    if email is not None:
        parts.append(f"[identity]\ncommit_email = {json.dumps(email)}\n")
    if paths:
        rows = "".join(f"{k} = {json.dumps(list(v))}\n" for k, v in paths.items())
        parts.append("[paths]\n" + rows)
    if limits:
        rows = "".join(f"{k} = {v}\n" for k, v in limits.items())
        parts.append("[limits]\n" + rows)
    if mode is not None:
        parts.append(f"[attribution]\nmode = {json.dumps(mode)}\n")
    if extra:
        parts.append(extra)
    return "\n".join(parts)


DEFAULT_CONFIG = make_config()


def lines(count: int, word: str = "x") -> str:
    """Returns a text of ``count`` identical lines.

    Args:
        count: Number of lines.
        word: Content of each line.

    Returns:
        The text, each line ending in a line feed.
    """
    return f"{word}\n" * count


def pr_body(reason: Optional[str] = None) -> str:
    """Builds a PR description with the four template sections.

    Args:
        reason: Raw text placed under "Soft-limit reason", or None for an
            empty section.

    Returns:
        The description text.
    """
    text = (
        "## Why\n\nBecause.\n\n## What\n\nChanged things.\n\n"
        "## Checks\n\nRan tests.\n\n## Soft-limit reason\n\n"
    )
    return text if reason is None else text + reason + "\n"


EN_BODY = (
    "# Title\n\n## Section\n\nSome text.\n\n"
    "| A | B |\n| --- | --- |\n| 1 | 2 |\n\n### Detail\n\nMore text.\n"
)
ZH_BODY = (
    "# 标题\n\n## 章节\n\n一些文字。\n\n"
    "| 甲 | 乙 |\n| --- | --- |\n| 1 | 2 |\n\n### 细节\n\n更多文字。\n"
)


def doc_text(
    lang: str = "en",
    doc_id: str = "x",
    version: str = "1.0",
    body: Optional[str] = None,
    name: str = "x",
    partner: Optional[str] = None,
    omit: Iterable[str] = (),
    raw: Optional[Mapping[str, str]] = None,
    updated: str = "2026-11-05",
) -> str:
    """Builds a troy-mode document with quoted front matter.

    Args:
        lang: ``en`` or ``zh-CN``. It picks the pointer key and the defaults.
        doc_id: Value of ``troy-doc``.
        version: Value of ``version``.
        body: Text after the front matter. Defaults to a standard body.
        name: File stem used for the default partner name.
        partner: Value of the ``mirror`` or ``mirror-of`` pointer.
        omit: Front matter keys to leave out.
        raw: Front matter keys mapped to a raw, unquoted-as-given value.
        updated: Value of ``updated``.

    Returns:
        The document text.
    """
    english = lang == "en"
    if partner is None:
        partner = f"{name}.zh-CN.md" if english else f"{name}.md"
    fields = [
        ("troy-doc", doc_id),
        ("lang", lang),
        ("version", version),
        ("updated", updated),
        ("status", "Draft" if english else "草稿"),
        ("mirror" if english else "mirror-of", partner),
    ]
    overrides = dict(raw or {})
    rows = []
    for key, value in fields:
        if key in omit:
            continue
        shown = overrides.get(key, json.dumps(value, ensure_ascii=False))
        rows.append(f"{key}: {shown}")
    default = EN_BODY if english else ZH_BODY
    return "---\n" + "\n".join(rows) + "\n---\n\n" + (body or default)


def doc_pair(
    name: str = "x",
    doc_id: Optional[str] = None,
    version: str = "1.0",
    zh_version: Optional[str] = None,
    en_body: Optional[str] = None,
    zh_body: Optional[str] = None,
    en_kwargs: Optional[Mapping] = None,
    zh_kwargs: Optional[Mapping] = None,
) -> dict:
    """Builds an English document and its Chinese mirror under ``docs/``.

    Args:
        name: File stem. The files are ``docs/<name>.md`` and
            ``docs/<name>.zh-CN.md``.
        doc_id: ``troy-doc`` value. Defaults to the name.
        version: Version of the English file.
        zh_version: Version of the Chinese file. Defaults to ``version``.
        en_body: Body of the English file.
        zh_body: Body of the Chinese file.
        en_kwargs: Extra keyword arguments for the English ``doc_text``.
        zh_kwargs: Extra keyword arguments for the Chinese ``doc_text``.

    Returns:
        A mapping of the two paths to their text.
    """
    base = {"doc_id": doc_id or name, "name": name}
    en = doc_text("en", **{**base, "version": version, "body": en_body, **dict(en_kwargs or {})})
    zh_args = {**base, "version": zh_version or version, "body": zh_body}
    zh = doc_text("zh-CN", **{**zh_args, **dict(zh_kwargs or {})})
    return {f"docs/{name}.md": en, f"docs/{name}.zh-CN.md": zh}
