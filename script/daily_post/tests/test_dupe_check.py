import json
import subprocess
import sys
from pathlib import Path

import pytest

from script.daily_post.corpus import Post, load_posts
from script.daily_post.dupe_check import DEFAULT_THRESHOLD, Match, rank

REPO = Path(__file__).resolve().parents[3]


def make_post(slug: str, title: str, description: str = "", headings=()) -> Post:
    return Post(
        slug=slug,
        title=title,
        description=description,
        headings=tuple(headings),
        path=Path(f"_posts/{slug}.md"),
    )


def test_rank_returns_matches_sorted_by_descending_score():
    posts = [
        make_post("kafka-to-nats", "From Kafka to NATS in distributed messaging"),
        make_post("pandas-speed", "Making Pandas dataframes faster"),
    ]
    matches = rank("Migrating from Kafka to NATS", posts)
    assert [m.slug for m in matches] == ["kafka-to-nats", "pandas-speed"]
    assert matches[0].score > matches[1].score


def test_rank_honours_the_top_argument():
    posts = [make_post(f"p{i}", f"Post about topic {i}") for i in range(10)]
    assert len(rank("topic 3", posts, top=3)) == 3


def test_rank_on_an_empty_corpus_returns_nothing():
    assert rank("anything", []) == []


def test_match_is_comparable_for_assertions():
    assert Match(slug="a", title="A", score=1.0) == Match(slug="a", title="A", score=1.0)


@pytest.mark.calibration
def test_threshold_flags_a_real_near_duplicate_and_spares_a_distinct_topic():
    """Pin DEFAULT_THRESHOLD against the live archive.

    "Migrating from Kafka to NATS" must collide with the existing Kafka/NATS post.
    "Postgres connection pooling under load" shares the corpus's general vocabulary
    but is a genuinely new topic and must stay clear of the threshold.
    """
    posts = load_posts(REPO / "_posts")
    assert len(posts) >= 140, "archive did not load; fixture assumptions are stale"

    duplicate = rank("Migrating from Kafka to NATS", posts)[0]
    assert duplicate.slug == "kafka-to-nats"
    assert duplicate.score > DEFAULT_THRESHOLD

    distinct = rank("Postgres connection pooling under sustained load", posts)[0]
    assert distinct.score < DEFAULT_THRESHOLD


def test_cli_exits_zero_for_a_viable_topic(tmp_path: Path):
    posts = tmp_path / "_posts"
    posts.mkdir()
    (posts / "2025-01-01-pandas.md").write_text(
        '---\ntitle: "Pandas performance"\ndescription: "d"\n---\n\nbody\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "script/daily_post/dupe_check.py",
         "--title", "Kubernetes operator patterns", "--posts-dir", str(posts)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_cli_exits_one_and_emits_json_for_a_duplicate(tmp_path: Path):
    posts = tmp_path / "_posts"
    posts.mkdir()
    (posts / "2025-01-01-pandas.md").write_text(
        '---\ntitle: "Pandas performance tuning"\n'
        'description: "Making Pandas dataframes faster"\n---\n\nbody\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "script/daily_post/dupe_check.py",
         "--title", "Pandas performance tuning",
         "--posts-dir", str(posts), "--json"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["duplicate"] is True
    assert payload["matches"][0]["slug"] == "pandas"
