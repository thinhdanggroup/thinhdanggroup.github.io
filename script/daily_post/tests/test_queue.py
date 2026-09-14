from pathlib import Path

import pytest
import yaml

from script.daily_post.queue import (
    QueueError,
    claim,
    load_topics,
    mark,
    next_queued,
)

QUEUE = """topics:
  - id: nats-jetstream-backpressure
    title: "JetStream backpressure in practice"
    angle: "What happens when consumers fall behind"
    category: distributed-systems
    tags: [NATS, Distributed Systems]
    status: published
    claimed_on: "2026-09-10"
    slug: jetstream-backpressure
  - id: pg-connection-pooling
    title: "Postgres connection pooling under load"
    angle: "pgbouncer modes and when each one bites"
    category: databases
    tags: [PostgreSQL]
    status: queued
  - id: python-free-threading
    title: "Free-threaded Python in anger"
    angle: "Measuring the GIL removal on real workloads"
    category: python
    tags: [Python]
    status: queued
"""


@pytest.fixture
def queue_path(tmp_path: Path) -> Path:
    p = tmp_path / "topic_queue.yml"
    p.write_text(QUEUE, encoding="utf-8")
    return p


def test_load_topics_reads_every_entry(queue_path: Path):
    assert len(load_topics(queue_path)) == 3


def test_load_topics_defaults_status_to_queued(tmp_path: Path):
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - id: x\n    title: "T"\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n",
        encoding="utf-8",
    )
    assert load_topics(p)[0].status == "queued"


def test_load_topics_rejects_an_unknown_status(tmp_path: Path):
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - id: x\n    title: "T"\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n    status: banana\n",
        encoding="utf-8",
    )
    with pytest.raises(QueueError, match="banana"):
        load_topics(p)


def test_load_topics_rejects_an_unknown_category(tmp_path: Path):
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - id: x\n    title: "T"\n    angle: "A"\n'
        "    category: knitting\n    tags: [Python]\n",
        encoding="utf-8",
    )
    with pytest.raises(QueueError, match="knitting"):
        load_topics(p)


def test_load_topics_rejects_duplicate_ids(tmp_path: Path):
    p = tmp_path / "q.yml"
    entry = (
        '  - id: dup\n    title: "T"\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n"
    )
    p.write_text("topics:\n" + entry + entry, encoding="utf-8")
    with pytest.raises(QueueError, match="dup"):
        load_topics(p)


def test_load_topics_on_a_missing_file_returns_empty(tmp_path: Path):
    assert load_topics(tmp_path / "absent.yml") == []


def test_next_queued_skips_non_queued_entries(queue_path: Path):
    topic = next_queued(load_topics(queue_path))
    assert topic is not None
    assert topic.id == "pg-connection-pooling"


def test_next_queued_returns_none_when_nothing_is_queued(queue_path: Path):
    topics = load_topics(queue_path)
    for t in topics:
        t.status = "published"
    assert next_queued(topics) is None


def test_claim_persists_status_and_date(queue_path: Path):
    claim(queue_path, "pg-connection-pooling", on="2026-09-14")
    data = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
    entry = next(t for t in data["topics"] if t["id"] == "pg-connection-pooling")
    assert entry["status"] == "claimed"
    assert entry["claimed_on"] == "2026-09-14"


def test_claim_preserves_the_other_entries(queue_path: Path):
    claim(queue_path, "pg-connection-pooling", on="2026-09-14")
    topics = load_topics(queue_path)
    assert [t.id for t in topics] == [
        "nats-jetstream-backpressure",
        "pg-connection-pooling",
        "python-free-threading",
    ]
    assert topics[2].status == "queued"


def test_claim_on_an_unknown_id_raises(queue_path: Path):
    with pytest.raises(QueueError, match="nope"):
        claim(queue_path, "nope", on="2026-09-14")


def test_claim_on_an_already_claimed_topic_raises(queue_path: Path):
    claim(queue_path, "pg-connection-pooling", on="2026-09-14")
    with pytest.raises(QueueError, match="not queued"):
        claim(queue_path, "pg-connection-pooling", on="2026-09-15")


def test_mark_records_the_published_slug(queue_path: Path):
    mark(queue_path, "pg-connection-pooling", "published", slug="pg-pooling")
    entry = next(t for t in load_topics(queue_path) if t.id == "pg-connection-pooling")
    assert entry.status == "published"
    assert entry.slug == "pg-pooling"


def test_mark_rejects_an_invalid_status(queue_path: Path):
    with pytest.raises(QueueError, match="banana"):
        mark(queue_path, "pg-connection-pooling", "banana")
