#!/usr/bin/env python3
"""Enforce the post front matter contract documented in README.md.

Run locally with `python script/check_frontmatter.py`; CI runs it on every PR.
Exits non-zero and lists every offending post.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
POSTS = REPO / "_posts"

CATEGORIES = {
    "ai-engineering",
    "databases",
    "distributed-systems",
    "infrastructure",
    "python",
    "software-engineering",
    "web-development",
}

DESC_MIN, DESC_MAX = 50, 200
FM_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.S)


def image_refs(text: str) -> list[str]:
    """Every asset reference, with or without a leading slash.

    The relative form (`assets/images/...`, no slash) is easy to miss with a
    naive `/assets/...` pattern and has silently broken images before, so both
    spellings are collected here and normalised to a leading slash.
    """
    found = re.findall(r"(?<![\w/])/?assets/images/[A-Za-z0-9._/-]+", text)
    return ["/" + r.lstrip("/").rstrip(".,);") for r in found]


FENCE_RE = re.compile(r"^(```|~~~)")


def unescaped_liquid(text: str) -> list[int]:
    """Line numbers of code fences holding Liquid that isn't inside {% raw %}.

    Jekyll renders Liquid everywhere, code fences included, so a Go template
    (`{{.Size}}`) or a GitHub Actions expression (`${{ matrix.os }}`) is
    evaluated and silently erased from the published page.
    """
    hits: list[int] = []
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        marker, start = m.group(1), i
        block = [lines[i]]
        i += 1
        while i < n and not lines[i].startswith(marker):
            block.append(lines[i])
            i += 1
        if i < n:
            block.append(lines[i])
            i += 1
        body = "\n".join(block)
        # {% raw %} normally wraps the fence from the outside, so look there too
        wrapped = (start > 0 and lines[start - 1].strip() == "{% raw %}") \
            or "{% raw %}" in body
        if ("{{" in body or "{%" in body) and not wrapped:
            hits.append(start + 1)
    return hits


def main() -> int:
    problems: list[str] = []
    posts = sorted(POSTS.glob("*.md"))
    if not posts:
        print("no posts found", file=sys.stderr)
        return 1

    for path in posts:
        name = path.name
        text = path.read_text(encoding="utf-8")

        if " " in name:
            problems.append(f"{name}: filename contains a space (breaks the URL)")

        m = FM_RE.match(text)
        if not m:
            problems.append(f"{name}: missing front matter")
            continue

        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            problems.append(f"{name}: front matter is not valid YAML ({e.__class__.__name__})")
            continue

        desc = fm.get("description")
        if not desc:
            problems.append(f"{name}: no description (used as the meta description)")
        elif not DESC_MIN <= len(desc) <= DESC_MAX:
            problems.append(f"{name}: description is {len(desc)} chars, want {DESC_MIN}-{DESC_MAX}")

        if not fm.get("tags"):
            problems.append(f"{name}: no tags")

        cats = fm.get("categories") or []
        if isinstance(cats, str):
            cats = [cats]
        if not cats:
            problems.append(f"{name}: no category")
        else:
            bad = [c for c in cats if c not in CATEGORIES]
            if bad:
                problems.append(
                    f"{name}: unknown category {bad!r}; allowed: {sorted(CATEGORIES)}"
                )

        header = fm.get("header") or {}
        for key in ("overlay_image", "teaser"):
            ref = header.get(key)
            if not ref:
                continue
            if not str(ref).endswith(".webp"):
                problems.append(f"{name}: header.{key} is not .webp ({ref})")

        # every local image reference must exist on disk
        for ref in image_refs(text):
            if not (REPO / ref.lstrip("/")).is_file():
                problems.append(f"{name}: broken image reference {ref}")

        for line_no in unescaped_liquid(text):
            problems.append(
                f"{name}: line {line_no} — code fence contains Liquid syntax "
                "({{ }} or {% %}) and is not wrapped in {% raw %}; Jekyll will "
                "evaluate and delete it"
            )

    if problems:
        print(f"{len(problems)} problem(s) across {len(posts)} posts:\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"OK: {len(posts)} posts satisfy the front matter contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
