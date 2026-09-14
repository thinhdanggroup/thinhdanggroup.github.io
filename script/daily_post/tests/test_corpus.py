from pathlib import Path

import pytest

from script.daily_post.corpus import Post, load_posts

POST = """---
title: "From Kafka to NATS: When Less Is More"
description: "When NATS is the better fit than Kafka."
categories:
    - distributed-systems
tags:
    - Kafka
---

Intro paragraph.

## The failure mode

Body.

### A subsection that should be ignored

More body.

## Key takeaways

Done.
"""


@pytest.fixture
def posts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "_posts"
    d.mkdir()
    (d / "2025-12-04-kafka-to-nats.md").write_text(POST, encoding="utf-8")
    return d


def test_load_posts_reads_title_and_description(posts_dir: Path):
    (post,) = load_posts(posts_dir)
    assert post.title == "From Kafka to NATS: When Less Is More"
    assert post.description == "When NATS is the better fit than Kafka."


def test_load_posts_derives_slug_from_filename_without_date(posts_dir: Path):
    (post,) = load_posts(posts_dir)
    assert post.slug == "kafka-to-nats"


def test_load_posts_collects_h2_headings_only(posts_dir: Path):
    (post,) = load_posts(posts_dir)
    assert post.headings == ("The failure mode", "Key takeaways")


def test_post_text_concatenates_the_searchable_fields():
    post = Post(
        slug="s", title="T", description="D", headings=("H1", "H2"), path=Path("x")
    )
    assert post.text == "T D H1 H2"


def test_load_posts_skips_files_without_front_matter(tmp_path: Path):
    d = tmp_path / "_posts"
    d.mkdir()
    (d / "2025-01-01-broken.md").write_text("no front matter here", encoding="utf-8")
    assert load_posts(d) == []


def test_load_posts_tolerates_invalid_yaml(tmp_path: Path):
    d = tmp_path / "_posts"
    d.mkdir()
    (d / "2025-01-01-bad.md").write_text(
        '---\ntitle: "unclosed\n---\n\nbody\n', encoding="utf-8"
    )
    assert load_posts(d) == []


def test_load_posts_ignores_h2_inside_backtick_fence(tmp_path: Path):
    """H2 lines inside ``` fences should not appear in headings."""
    d = tmp_path / "_posts"
    d.mkdir()
    post_with_fence = """---
title: "Code Example"
description: "A post with code."
---

## Real Heading

Here is some code:

```python
## This is a comment in code
def foo():
    pass
```

## Another Real Heading
"""
    (d / "2025-01-01-fence.md").write_text(post_with_fence, encoding="utf-8")
    (post,) = load_posts(d)
    assert "This is a comment in code" not in post.headings
    assert post.headings == ("Real Heading", "Another Real Heading")


def test_load_posts_ignores_h2_inside_tilde_fence(tmp_path: Path):
    """H2 lines inside ~~~ fences should not appear in headings."""
    d = tmp_path / "_posts"
    d.mkdir()
    post_with_fence = """---
title: "Code Example"
description: "A post with code."
---

## Real Heading

Here is some code:

~~~python
## This is a comment in code
def foo():
    pass
~~~

## Another Real Heading
"""
    (d / "2025-01-01-tilde.md").write_text(post_with_fence, encoding="utf-8")
    (post,) = load_posts(d)
    assert "This is a comment in code" not in post.headings
    assert post.headings == ("Real Heading", "Another Real Heading")


def test_load_posts_skips_files_with_invalid_utf8(tmp_path: Path):
    """Files with invalid UTF-8 should be skipped, not crash."""
    d = tmp_path / "_posts"
    d.mkdir()
    # Write a valid post first
    valid_post = """---
title: "Valid Post"
description: "This is valid."
---

## Good Heading
"""
    (d / "2025-01-01-valid.md").write_text(valid_post, encoding="utf-8")

    # Write a file with invalid UTF-8 bytes
    (d / "2025-01-02-invalid.md").write_bytes(
        b"---\ntitle: \"Bad\"\n---\n\nBody with \xff invalid bytes\n"
    )

    # Should return only the valid post
    posts = load_posts(d)
    assert len(posts) == 1
    assert posts[0].title == "Valid Post"
