#!/usr/bin/env python3
"""Enforce the post front matter contract documented in README.md.

Run locally with `python script/check_frontmatter.py`; CI runs it on every PR.
Exits non-zero and lists every offending post.
"""
from __future__ import annotations

import re
import sys
from collections import namedtuple
from collections.abc import Iterator
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

Fence = namedtuple("Fence", "line info body text closed raw_wrapped")


def code_fences(text: str) -> Iterator[Fence]:
    """Walk every fenced code block in a post exactly once.

    Both fence checks below — unescaped Liquid and malformed Mermaid — need the
    same walk, so it lives here instead of being written out twice and drifting.

    `line` is the 1-based line number of the opening fence; `info` its info
    string (``mermaid``, ``python``, or empty); `body` the lines strictly
    between the fences; `text` the whole block, fences included; `closed`
    whether a closing fence was actually found; and `raw_wrapped` whether the
    line immediately above is `{% raw %}`, which is how a fence is normally
    wrapped from the outside.
    """
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        marker, start = m.group(1), i
        info = lines[i][len(marker):].strip()
        block = [lines[i]]
        body: list[str] = []
        i += 1
        while i < n and not lines[i].startswith(marker):
            body.append(lines[i])
            block.append(lines[i])
            i += 1
        closed = i < n
        if closed:
            block.append(lines[i])
            i += 1
        yield Fence(
            line=start + 1,
            info=info,
            body=body,
            text="\n".join(block),
            closed=closed,
            raw_wrapped=start > 0 and lines[start - 1].strip() == "{% raw %}",
        )


def unescaped_liquid(text: str) -> list[int]:
    """Line numbers of code fences holding Liquid that isn't inside {% raw %}.

    Jekyll renders Liquid everywhere, code fences included, so a Go template
    (`{{.Size}}`) or a GitHub Actions expression (`${{ matrix.os }}`) is
    evaluated and silently erased from the published page.
    """
    hits: list[int] = []
    for fence in code_fences(text):
        # {% raw %} normally wraps the fence from the outside, so look there too
        wrapped = fence.raw_wrapped or "{% raw %}" in fence.text
        if ("{{" in fence.text or "{%" in fence.text) and not wrapped:
            hits.append(fence.line)
    return hits


# Diagram types Mermaid 10.6.1 can actually parse — the version
# `_includes/head/custom.html` pins on the CDN. Anything outside this set is a
# parse failure, which Mermaid reports by painting a red error box into the
# published page.
#
# Matched case-insensitively, so the set is written lowercase. Deliberately
# absent are the types introduced in Mermaid 11 — `block-beta`, `packet-beta`,
# `architecture-beta`, `kanban`, `radar` — because a post using one would render
# an error box against the pinned 10.6.1 runtime, which is exactly what this
# check exists to catch.
MERMAID_TYPES = {
    "c4component",
    "c4container",
    "c4context",
    "c4deployment",
    "c4dynamic",
    "classdiagram",
    "classdiagram-v2",
    "erdiagram",
    "flowchart",
    "flowchart-elk",
    "flowchart-v2",
    "gantt",
    "gitgraph",
    "graph",
    "info",
    "journey",
    "mindmap",
    "pie",
    "quadrantchart",
    "requirementdiagram",
    "sankey-beta",
    "sequencediagram",
    "statediagram",
    "statediagram-v2",
    "timeline",
    "xychart-beta",
    "zenuml",
}


def mermaid_declaration(body: list[str]) -> str | None:
    """The diagram-type keyword a Mermaid block declares, or None if it has none.

    Three things are legally allowed ahead of the declaration and are skipped on
    the way to it: blank lines, `%%` comments and `%%{init: ...}%%` directives,
    and a leading `---` YAML front matter block of Mermaid's own.
    """
    lines = [line.strip() for line in body]
    i = 0
    while i < len(lines) and not lines[i]:
        i += 1
    if i < len(lines) and lines[i] == "---":  # Mermaid's own front matter block
        i += 1
        while i < len(lines) and lines[i] != "---":
            i += 1
        i += 1
    for line in lines[i:]:
        if not line or line.startswith("%%"):
            continue
        return line.split()[0].rstrip(":;")
    return None


def mermaid_problems(text: str) -> list[tuple[int, str]]:
    """(line number, what is wrong) for every malformed ```mermaid block.

    The theme renders these in the browser: `_includes/head/custom.html` loads
    Mermaid 10.6.1 from the CDN on demand for any `pre code.language-mermaid`.
    Mermaid reports a parse failure by drawing a visible error box where the
    diagram should be — the Jekyll build succeeds, htmlproofer sees nothing
    wrong, and the breakage is only visible to a reader.

    So the check is structural and pure standard library on purpose. Really
    parsing the diagram would mean shelling out to `mermaid-cli`, i.e. depending
    on `node` being on PATH, and this repo has already been burned by a tool
    that was installed but not on the pipeline's PATH.
    """
    problems: list[tuple[int, str]] = []
    for fence in code_fences(text):
        if fence.info.lower() != "mermaid":
            continue

        if not fence.closed:
            problems.append((
                fence.line,
                "```mermaid block is never closed; the rest of the post is "
                "swallowed into the diagram",
            ))
            continue

        if not any(line.strip() for line in fence.body):
            problems.append((
                fence.line,
                "```mermaid block is empty; Mermaid renders an error box, not "
                "nothing",
            ))
            continue

        if any("\t" in line for line in fence.body):
            problems.append((
                fence.line,
                "```mermaid block contains a tab character; Mermaid's parser is "
                "whitespace-sensitive and rejects tabs — indent with spaces",
            ))

        if "{{" in fence.text or "{%" in fence.text:
            problems.append((
                fence.line,
                "```mermaid block contains Liquid syntax ({{ }} or {% %}); "
                "Jekyll evaluates it and the diagram source reaches the browser "
                "mangled. A diagram cannot be fixed with {% raw %} either — "
                "rewrite the node labels without braces",
            ))

        declared = mermaid_declaration(fence.body)
        if declared is None:
            problems.append((
                fence.line,
                "```mermaid block declares no diagram type; its first real line "
                "must name one (e.g. `sequenceDiagram`, `flowchart TD`)",
            ))
        elif declared.lower() not in MERMAID_TYPES:
            problems.append((
                fence.line,
                f"```mermaid block declares unknown diagram type {declared!r}; "
                "Mermaid 10.6.1 draws an error box for anything outside "
                "sequenceDiagram / flowchart / graph / stateDiagram-v2 / "
                "classDiagram / erDiagram and the rest of MERMAID_TYPES in "
                "script/check_frontmatter.py",
            ))
    return problems


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

        for line_no, problem in mermaid_problems(text):
            problems.append(f"{name}: line {line_no} — {problem}")

    if problems:
        print(f"{len(problems)} problem(s) across {len(posts)} posts:\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"OK: {len(posts)} posts satisfy the front matter contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
