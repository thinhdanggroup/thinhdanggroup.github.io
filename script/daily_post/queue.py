#!/usr/bin/env python3
"""Read and update the daily post topic queue at `_data/topic_queue.yml`.

The queue is committed state: the operator edits it by hand to steer what gets
written, and the pipeline writes back claim and publish status. Every mutation
rewrites the whole file, which is safe at this size and keeps the diff readable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

VALID_STATUSES = ("queued", "claimed", "published", "rejected")

CATEGORIES = (
    "ai-engineering",
    "databases",
    "distributed-systems",
    "infrastructure",
    "python",
    "software-engineering",
    "web-development",
)


class QueueError(Exception):
    """The queue file is malformed, or the requested transition is not legal."""


@dataclass
class Topic:
    id: str
    title: str
    angle: str
    category: str
    tags: list[str] = field(default_factory=list)
    status: str = "queued"
    claimed_on: str | None = None
    slug: str | None = None


def load_topics(path: Path) -> list[Topic]:
    """Every topic in the queue. A missing file is an empty queue, not an error."""
    if not path.is_file():
        return []

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("topics") or []

    topics: list[Topic] = []
    seen: set[str] = set()
    for entry in entries:
        topic = Topic(
            id=str(entry["id"]),
            title=str(entry["title"]),
            angle=str(entry.get("angle") or ""),
            category=str(entry.get("category") or ""),
            tags=list(entry.get("tags") or []),
            status=str(entry.get("status") or "queued"),
            claimed_on=entry.get("claimed_on"),
            slug=entry.get("slug"),
        )
        if topic.id in seen:
            raise QueueError(f"duplicate topic id: {topic.id}")
        if topic.status not in VALID_STATUSES:
            raise QueueError(
                f"{topic.id}: unknown status {topic.status!r}; "
                f"allowed: {list(VALID_STATUSES)}"
            )
        if topic.category not in CATEGORIES:
            raise QueueError(
                f"{topic.id}: unknown category {topic.category!r}; "
                f"allowed: {list(CATEGORIES)}"
            )
        seen.add(topic.id)
        topics.append(topic)
    return topics


def next_queued(topics: list[Topic]) -> Topic | None:
    """The first topic still waiting to be written, or None if the queue is dry."""
    for topic in topics:
        if topic.status == "queued":
            return topic
    return None


def claim(path: Path, topic_id: str, on: str) -> Topic:
    """Move a queued topic to `claimed`, stamping the run date.

    Claiming is what stops a second run on the same day from picking the same
    topic, so it must happen before any research work begins.
    """
    topics = load_topics(path)
    topic = _find(topics, topic_id)
    if topic.status != "queued":
        raise QueueError(f"{topic_id}: not queued (status is {topic.status!r})")
    topic.status = "claimed"
    topic.claimed_on = on
    _write(path, topics)
    return topic


def mark(path: Path, topic_id: str, status: str, slug: str | None = None) -> Topic:
    """Set a topic's terminal status, optionally recording the published slug."""
    if status not in VALID_STATUSES:
        raise QueueError(f"unknown status {status!r}; allowed: {list(VALID_STATUSES)}")
    topics = load_topics(path)
    topic = _find(topics, topic_id)
    topic.status = status
    if slug is not None:
        topic.slug = slug
    _write(path, topics)
    return topic


def _find(topics: list[Topic], topic_id: str) -> Topic:
    for topic in topics:
        if topic.id == topic_id:
            return topic
    raise QueueError(f"no topic with id {topic_id!r}")


def _write(path: Path, topics: list[Topic]) -> None:
    payload = {"topics": [_entry(t) for t in topics]}
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def _entry(topic: Topic) -> dict:
    """Serialise a topic, omitting keys that are still unset to keep the file clean."""
    entry = {
        "id": topic.id,
        "title": topic.title,
        "angle": topic.angle,
        "category": topic.category,
        "tags": topic.tags,
        "status": topic.status,
    }
    if topic.claimed_on:
        entry["claimed_on"] = topic.claimed_on
    if topic.slug:
        entry["slug"] = topic.slug
    return entry
