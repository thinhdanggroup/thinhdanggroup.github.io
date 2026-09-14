import os
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


def test_claim_preserves_comment_header(tmp_path: Path):
    """CRITICAL FIX: comment headers must survive a claim() call."""
    p = tmp_path / "topic_queue.yml"
    queue_with_header = """# Topics for the daily post pipeline.
#
# The pipeline takes the first entry with `status: queued`, marks it `claimed`,
# and writes it. When the queue is dry it discovers a topic from the web instead,
# so keeping entries here is how you steer what gets written.
#
# status: queued | claimed | published | rejected
# category: one of ai-engineering, databases, distributed-systems
topics:
  - id: test-topic
    title: "Test topic"
    angle: "Test angle"
    category: databases
    tags: [Test]
    status: queued
"""
    p.write_text(queue_with_header, encoding="utf-8")

    # Call claim() on the test topic
    claim(p, "test-topic", on="2026-09-14")

    # Read back the file and verify the comment header is still present
    content = p.read_text(encoding="utf-8")
    assert "# Topics for the daily post pipeline." in content
    assert "# The pipeline takes the first entry with" in content
    assert "# status: queued | claimed | published | rejected" in content


def test_claim_preserves_unmodeled_keys(tmp_path: Path):
    """CRITICAL FIX: unmodeled keys (like notes:) must survive a claim() call."""
    p = tmp_path / "topic_queue.yml"
    queue_with_extra_key = """topics:
  - id: test-topic
    title: "Test topic"
    angle: "Test angle"
    category: databases
    tags: [Test]
    status: queued
    notes: "This is an important note from the operator"
"""
    p.write_text(queue_with_extra_key, encoding="utf-8")

    # Call claim() on the test topic
    claim(p, "test-topic", on="2026-09-14")

    # Read back the file and verify the unmodeled 'notes' key is still present
    content = p.read_text(encoding="utf-8")
    assert "notes:" in content
    assert "This is an important note from the operator" in content


def test_load_topics_raises_queueerror_on_missing_id(tmp_path: Path):
    """FINDING 3: Missing 'id' must raise QueueError, not KeyError."""
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - title: "T"\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n",
        encoding="utf-8",
    )
    with pytest.raises(QueueError, match="missing or empty 'id'"):
        load_topics(p)


def test_load_topics_raises_queueerror_on_missing_title(tmp_path: Path):
    """FINDING 3: Missing 'title' must raise QueueError, not KeyError."""
    p = tmp_path / "q.yml"
    p.write_text(
        'topics:\n  - id: x\n    angle: "A"\n'
        "    category: python\n    tags: [Python]\n",
        encoding="utf-8",
    )
    with pytest.raises(QueueError, match="missing or empty 'title'"):
        load_topics(p)


def test_write_is_atomic_no_temp_files_left(tmp_path: Path):
    """FINDING 2: After claim(), no temporary files should remain."""
    p = tmp_path / "topic_queue.yml"
    queue = """topics:
  - id: test-topic
    title: "Test topic"
    angle: "Test angle"
    category: databases
    tags: [Test]
    status: queued
"""
    p.write_text(queue, encoding="utf-8")

    # Call claim() on the test topic
    claim(p, "test-topic", on="2026-09-14")

    # Check that no temporary files are left in the directory
    leftover_files = [f for f in os.listdir(tmp_path) if ".topic_queue_tmp_" in f]
    assert len(leftover_files) == 0, f"Leftover temp files found: {leftover_files}"


def test_file_permissions_preserved_after_claim(tmp_path: Path):
    """FINDING 4: File permissions must be preserved after claim()."""
    p = tmp_path / "topic_queue.yml"
    queue = """topics:
  - id: test-topic
    title: "Test topic"
    angle: "Test angle"
    category: databases
    tags: [Test]
    status: queued
"""
    p.write_text(queue, encoding="utf-8")

    # Set a specific mode on the file
    os.chmod(p, 0o644)
    mode_before = oct(os.stat(p).st_mode)[-3:]

    # Call claim()
    claim(p, "test-topic", on="2026-09-14")

    # Verify the mode is unchanged
    mode_after = oct(os.stat(p).st_mode)[-3:]
    assert mode_before == mode_after == "644", f"Mode changed from {mode_before} to {mode_after}"


def test_minimal_diff_on_claim(tmp_path: Path):
    """FINDING 5: claim() should produce a minimal diff touching only the claimed entry."""
    import difflib

    p = tmp_path / "topic_queue.yml"
    # Use the actual structure from the real seed file
    queue = """# Topics for the daily post pipeline.
#
# The pipeline steers what gets written.
topics:
  - id: first-topic
    title: "First topic"
    angle: "First angle"
    category: databases
    tags: [PostgreSQL, Performance]
    status: queued

  - id: second-topic
    title: "Second topic"
    angle: "Second angle"
    category: python
    tags: [Python, Performance]
    status: queued

  - id: third-topic
    title: "Third topic"
    angle: "Third angle"
    category: infrastructure
    tags: [Observability, Performance]
    status: queued
"""
    p.write_text(queue, encoding="utf-8")
    before = p.read_text(encoding="utf-8")

    # Claim the first topic
    claim(p, "first-topic", on="2026-09-14")
    after = p.read_text(encoding="utf-8")

    # Compute unified diff
    diff_lines = list(difflib.unified_diff(
        before.splitlines(), after.splitlines(), lineterm='',
        fromfile='before', tofile='after'
    ))

    # Count actual content changes (lines starting with + or - but not +++ or ---)
    content_changes = [
        line for line in diff_lines
        if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))
    ]

    # We expect exactly 3 changes:
    # - status: queued (removed)
    # + status: claimed (added)
    # + claimed_on: '2026-09-14' (added)
    assert len(content_changes) == 3, (
        f"Expected 3 content changes, got {len(content_changes)}\n"
        f"Changes: {content_changes}\n\nFull diff:\n" + "\n".join(diff_lines)
    )


def test_load_topics_raises_queueerror_on_malformed_entry(tmp_path: Path):
    """FINDING (bonus): Entry that is a bare string raises QueueError, not TypeError."""
    p = tmp_path / "q.yml"
    # YAML that parses to a list with a bare string entry
    p.write_text("topics:\n  - valid entry\n", encoding="utf-8")
    with pytest.raises(QueueError, match="must be a dict"):
        load_topics(p)
