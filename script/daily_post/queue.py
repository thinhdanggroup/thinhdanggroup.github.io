#!/usr/bin/env python3
"""Read and update the daily post topic queue at `_data/topic_queue.yml`.

The queue is committed state: the operator edits it by hand to steer what gets
written, and the pipeline writes back claim and publish status. Every mutation
round-trips the original file with round-trip YAML to preserve comments, key order,
and unmodeled keys.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from ruamel.yaml import YAML

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
    for idx, entry in enumerate(entries):
        # Validate entry is a dict, not a bare string or None
        if not isinstance(entry, dict):
            raise QueueError(
                f"entry {idx}: must be a dict, not {type(entry).__name__}"
            )
        # Validate required fields exist
        if "id" not in entry or not entry["id"]:
            raise QueueError(
                f"entry {idx}: missing or empty 'id' field"
            )
        if "title" not in entry or not entry["title"]:
            raise QueueError(
                f"entry {idx} ({entry.get('id', '?')}): missing or empty 'title' field"
            )

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
    _write(path, topic_id, topic)
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
    _write(path, topic_id, topic)
    return topic


def _find(topics: list[Topic], topic_id: str) -> Topic:
    for topic in topics:
        if topic.id == topic_id:
            return topic
    raise QueueError(f"no topic with id {topic_id!r}")


def _write(path: Path, topic_id: str, topic: Topic) -> None:
    """Round-trip the YAML file, updating only the specified topic entry.

    Loads the existing document (preserving comments, order, and unmodeled keys),
    mutates only the specified entry, writes atomically to a temp file, then swaps.
    Preserves file permissions and formatting to keep diffs minimal.
    """
    # Capture original file permissions before reading
    original_mode = None
    if path.is_file():
        try:
            original_mode = os.stat(path).st_mode
        except OSError:
            pass

    # Load with round-trip preservation and style matching
    yaml_handler = YAML()
    yaml_handler.preserve_quotes = True
    yaml_handler.default_flow_style = False
    # Configure indentation to match the source file style
    yaml_handler.indent(mapping=2, sequence=4, offset=2)

    if path.is_file():
        doc = yaml_handler.load(path.read_text(encoding="utf-8"))
    else:
        doc = {"topics": []}

    # Find and update the topic entry in the original document
    topics_list = doc.get("topics") or []
    for entry in topics_list:
        if entry.get("id") == topic_id:
            # Preserve trailing blank lines: move comment from last key to the new last key
            # This ensures blank-line separators appear after the entire entry, not within it
            last_key = list(entry.keys())[-1] if entry else None
            last_comment = None
            if last_key and hasattr(entry, "ca") and entry.ca and hasattr(entry.ca, "items"):
                last_comment = entry.ca.items.get(last_key)

            # Update the fields
            entry["status"] = topic.status
            if topic.claimed_on:
                entry["claimed_on"] = topic.claimed_on
            if topic.slug:
                entry["slug"] = topic.slug

            # Move the trailing comment to the new last key to maintain blank-line placement
            new_last_key = list(entry.keys())[-1]
            if last_comment and hasattr(entry, "ca") and entry.ca and hasattr(entry.ca, "items"):
                if last_key != new_last_key:
                    # Clear comment from old last key
                    entry.ca.items[last_key] = [None, None, None, None]
                    # Add it to new last key
                    entry.ca.items[new_last_key] = last_comment
            break

    # Write atomically: write to temp file in same directory, then swap
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent, prefix=".topic_queue_tmp_", suffix=".yml"
    )
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            yaml_handler.dump(doc, f)

        # Preserve file permissions: apply original mode to temp file
        if original_mode is not None:
            os.chmod(temp_path, original_mode)
        else:
            # Default to readable by all, writable by owner (644 in octal)
            os.chmod(temp_path, 0o644)

        os.replace(temp_path, path)
    except Exception:
        # Clean up temp file if something went wrong
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
