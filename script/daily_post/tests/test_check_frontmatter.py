"""Tests for the Mermaid validation in `script/check_frontmatter.py`.

A malformed Mermaid block is invisible to every other check in the pipeline: the
Jekyll build succeeds, htmlproofer sees a well-formed `<pre><code>`, and the
breakage only appears in the browser as Mermaid's red error box. This file pins
the structural check that catches it before the branch is pushed.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from script.check_frontmatter import (
    MERMAID_TYPES,
    main,
    mermaid_declaration,
    mermaid_problems,
    unescaped_liquid,
)

REPO = Path(__file__).resolve().parents[3]
POSTS = REPO / "_posts"

FRONT_MATTER = textwrap.dedent(
    """\
    ---
    title: "A post"
    description: "A description that is comfortably inside the fifty to two hundred character bound."
    categories: [databases]
    tags: [postgres]
    ---
    """
)


def post(body: str) -> str:
    return FRONT_MATTER + "\n" + textwrap.dedent(body)


# --- the valid case -------------------------------------------------------


def test_a_valid_sequence_diagram_passes():
    text = post(
        """
        ```mermaid
        sequenceDiagram
            participant C as Client
            participant P as PgBouncer
            C->>P: connect
            P-->>C: ready
        ```
        """
    )
    assert mermaid_problems(text) == []


@pytest.mark.parametrize(
    "declaration",
    [
        "sequenceDiagram",
        "flowchart TD",
        "graph LR;",
        "stateDiagram-v2",
        "classDiagram",
        "erDiagram",
        "gitGraph:",
        "pie title Cache hits",
    ],
)
def test_every_common_declaration_form_is_accepted(declaration: str):
    """Declarations carry arguments and trailing punctuation; the keyword is what matters."""
    text = post(f"\n```mermaid\n{declaration}\n    A --> B\n```\n")
    assert mermaid_problems(text) == []


def test_a_leading_directive_or_comment_does_not_hide_the_declaration():
    text = post(
        """
        ```mermaid
        %%{init: {'theme': 'neutral'}}%%
        %% the ordering is the point
        sequenceDiagram
            A->>B: hello
        ```
        """
    )
    assert mermaid_problems(text) == []


def test_non_mermaid_fences_are_left_alone():
    """A Python block full of tabs is not a Mermaid problem."""
    text = post("\n```python\ndef f():\n\tpass\n```\n")
    assert mermaid_problems(text) == []


# --- the four malformed cases ---------------------------------------------


def test_unknown_diagram_type_fails():
    text = post("\n```mermaid\nsequenceDigram\n    A->>B: typo\n```\n")
    problems = mermaid_problems(text)
    assert len(problems) == 1
    assert "unknown diagram type" in problems[0][1]
    assert "sequenceDigram" in problems[0][1]


def test_a_mermaid_11_only_type_fails_against_the_pinned_10_6_1():
    """The theme pins 10.6.1, so a v11 diagram type is an error box, not a diagram."""
    text = post("\n```mermaid\nblock-beta\n    columns 1\n```\n")
    assert any("unknown diagram type" in p for _, p in mermaid_problems(text))


def test_empty_block_fails():
    text = post("\n```mermaid\n\n```\n")
    problems = mermaid_problems(text)
    assert len(problems) == 1
    assert "empty" in problems[0][1]


def test_tab_indented_block_fails():
    text = post("\n```mermaid\nsequenceDiagram\n\tA->>B: tabbed\n```\n")
    assert any("tab character" in p for _, p in mermaid_problems(text))


def test_liquid_inside_a_mermaid_fence_fails():
    text = post("\n```mermaid\nflowchart TD\n    A[{{ site.title }}] --> B\n```\n")
    assert any("Liquid" in p for _, p in mermaid_problems(text))


def test_liquid_in_a_mermaid_fence_fails_even_when_raw_wrapped():
    """{% raw %} keeps Liquid off Jekyll's radar; it does not make Mermaid parse it."""
    text = post(
        "\n{% raw %}\n```mermaid\nflowchart TD\n    A[{{ x }}] --> B\n```\n{% endraw %}\n"
    )
    assert unescaped_liquid(text) == []  # the Liquid check is satisfied ...
    assert any("Liquid" in p for _, p in mermaid_problems(text))  # ... this one is not


# --- reporting and exit code ----------------------------------------------


def test_the_reported_line_number_points_at_the_opening_fence():
    text = post("\n```mermaid\nnotADiagram\n```\n")
    line_no, _ = mermaid_problems(text)[0]
    assert text.split("\n")[line_no - 1].startswith("```mermaid")


def test_an_unclosed_block_is_reported_rather_than_silently_swallowed():
    text = post("\n```mermaid\nsequenceDiagram\n    A->>B: hi\n")
    assert any("never closed" in p for _, p in mermaid_problems(text))


def test_a_malformed_diagram_makes_the_script_exit_non_zero(tmp_path, monkeypatch):
    """The problem has to reach the exit code, not just the helper's return value."""
    import script.check_frontmatter as cf

    posts = tmp_path / "_posts"
    posts.mkdir()
    (posts / "2026-01-01-broken.md").write_text(
        post("\n```mermaid\nsequenceDigram\n    A->>B: typo\n```\n"), encoding="utf-8"
    )
    monkeypatch.setattr(cf, "POSTS", posts)
    assert main() == 1


def test_the_same_fixture_passes_once_the_diagram_type_is_spelled_correctly(
    tmp_path, monkeypatch
):
    import script.check_frontmatter as cf

    posts = tmp_path / "_posts"
    posts.mkdir()
    (posts / "2026-01-01-fine.md").write_text(
        post("\n```mermaid\nsequenceDiagram\n    A->>B: typo\n```\n"), encoding="utf-8"
    )
    monkeypatch.setattr(cf, "POSTS", posts)
    assert main() == 0


# --- the live archive -----------------------------------------------------


def test_the_live_archive_still_passes():
    """Too strict a checker is a checker that fails on posts that actually render."""
    result = subprocess.run(
        [sys.executable, str(REPO / "script" / "check_frontmatter.py")],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_the_archives_only_diagram_post_is_accepted():
    text = (POSTS / "2024-07-15-essential-cache-concepts.md").read_text(encoding="utf-8")
    assert mermaid_problems(text) == []


def test_the_type_set_is_lowercase_because_matching_is_case_insensitive():
    assert all(t == t.lower() for t in MERMAID_TYPES)
    assert mermaid_declaration(["SequenceDiagram", "  A->>B: hi"]) == "SequenceDiagram"
    assert mermaid_problems("```mermaid\nSequenceDiagram\nA->>B: hi\n```") == []
