#!/usr/bin/env python3
"""Read `_posts/*.md` into records the dedupe check can compare against.

Deliberately reads the posts themselves rather than `blog_posts.json`: that export
carries only title, tags, and date, and goes stale the moment `make generate` has
not been run since the last post.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

FM_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.S)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
DATED_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")
FENCE_RE = re.compile(r"^(```|~~~)")


def _strip_fenced_code_blocks(text: str) -> str:
    """Remove fenced code blocks (``` and ~~~) from text.

    Returns text with code blocks removed so H2_RE doesn't match
    lines inside fences (e.g., code comments that happen to start with ##).
    """
    lines = text.split("\n")
    result: list[str] = []
    i, n = 0, len(lines)

    while i < n:
        m = FENCE_RE.match(lines[i])
        if not m:
            result.append(lines[i])
            i += 1
            continue

        # Found a fence opener; skip until we find the closer
        marker = m.group(1)
        i += 1
        while i < n and not lines[i].startswith(marker):
            i += 1
        # Skip the closing fence too
        if i < n:
            i += 1

    return "\n".join(result)


@dataclass(frozen=True)
class Post:
    slug: str
    title: str
    description: str
    headings: tuple[str, ...]
    path: Path

    @property
    def text(self) -> str:
        """The fields worth comparing a candidate topic against."""
        return " ".join([self.title, self.description, *self.headings])


def load_posts(posts_dir: Path) -> list[Post]:
    """Every parseable post. Unparseable files are skipped, not fatal.

    A single malformed post must never take down the daily run.
    """
    posts: list[Post] = []
    for path in sorted(posts_dir.glob("*.md")):
        post = _read_post(path)
        if post is not None:
            posts.append(post)
    return posts


def _read_post(path: Path) -> Post | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    match = FM_RE.match(text)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(fm, dict):
        return None

    body = text[match.end():]
    body_without_fences = _strip_fenced_code_blocks(body)
    name_match = DATED_NAME_RE.match(path.stem)
    slug = name_match.group(1) if name_match else path.stem

    return Post(
        slug=slug,
        title=str(fm.get("title") or ""),
        description=str(fm.get("description") or ""),
        headings=tuple(H2_RE.findall(body_without_fences)),
        path=path,
    )
