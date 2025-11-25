---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        - label: "Linkedin"
          icon: "fab fa-fw fa-linkedin"
          url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/postgres-as-a-message-bus/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/postgres-as-a-message-bus/banner.png
title: "Postgres as a Message Bus: Implementing Durable Event Queues with LISTEN/NOTIFY and Logical Decoding"
tags:
    - postgres
    - message bus
---

You’ve got a small-ish system: a monolith plus a couple of background workers, maybe one or two sidecar services.

You want events. You’d like to:

-   Emit “order.created” when an order row is inserted
-   Run background jobs when a user signs up
-   Invalidate cache entries when products change

And immediately someone says: _“We should add Kafka.”_

For many teams, that’s the moment when architecture complexity starts climbing faster than actual business value. You now have another clustered system to deploy, monitor, secure, and pay for.

But you already have a distributed log with strong durability guarantees sitting right there: **PostgreSQL**.

In this post we’ll walk through how to treat Postgres as your **event backbone**, using:

-   `LISTEN` / `NOTIFY` for lightweight, low-latency signaling ([PostgreSQL][1])
-   Tables + row locking as **durable queues**
-   **Logical decoding** to stream changes out of Postgres like a real message bus ([PostgreSQL][2])

The goal isn’t to “replace Kafka forever.” It’s to show you how far you can get with the database you already have before you introduce another moving part.

---

## What Do You Actually Need From a “Message Bus”?

Before we dive into Postgres specifics, let’s translate “I need Kafka” into concrete requirements.

Most event-driven systems actually need some subset of:

1. **Cross-process signaling**
   “When this happens over there, notify code running over here.”

2. **Durability & replay**
   If a consumer is down for a bit, it can **catch up** later.

3. **Ordering**
   At least _per key_ ordering (e.g., events for the same `order_id`).

4. **Backpressure**
   Events pile up somewhere safe instead of knocking your app over.

5. **At-least-once semantics**
   You can tolerate duplicate processing as long as you don’t lose events.

6. **Transactional coupling (the “outbox problem”)**
   Business changes and “events about those changes” should commit together.

For a ton of small and medium systems, you don’t actually need:

-   Tens of thousands of messages per second
-   Dozens of independent consumer groups
-   Cross-region event pipelines

You just need **a durable queue with wake-up notifications**, plus a way to fan out data to a few services.

And that’s exactly the niche where Postgres shines.

---

## A Primer on LISTEN / NOTIFY: Postgres as Pub/Sub

Postgres includes a built-in asynchronous notification mechanism:

-   `NOTIFY channel, 'payload'`
-   `LISTEN channel`

When a session calls `NOTIFY` on a channel, **all sessions that previously issued `LISTEN` on that channel get an asynchronous notification** with an optional payload string. ([PostgreSQL][3])

The payload:

-   Is just a string (often JSON or an ID)
-   In default config must be **less than 8000 bytes** ([PostgreSQL][1])

Crucially:

-   Notifications are **transactional**. If you `NOTIFY` inside a transaction, listeners only see it **after the transaction commits**. If the transaction rolls back, no notification is sent. ([Falcon][4])
-   Postgres preserves order: notifications from a single transaction are delivered in send order; notifications from different transactions are delivered in commit order. ([postgrespro.com][5])

### Tiny demo

Open two `psql` sessions connected to the same database.

**Session A**:

```sql
LISTEN app_events;
-- psql will now print async notifications as they arrive
```

**Session B**:

```sql
NOTIFY app_events, 'hello from B';
```

Session A will print something like:

```text
Asynchronous notification "app_events" with payload "hello from B" received from server process with PID 12345.
```

You’ve just done lightweight pub/sub _inside_ Postgres—no extra components.

So… why doesn’t everyone just use this as a queue?

---

## Why LISTEN/NOTIFY Alone Is Not a Queue

There are a few deal-breakers if you try to treat notifications themselves as the message store:

1. **Notifications are not persisted**
   They live in an in-memory queue. If a client is disconnected when a notification is sent, it simply **never sees it**. ([Compile N Run][6])

2. **No offsets or acks**
   You can’t ask Postgres: “What notifications did I miss between 14:03 and 14:05?” There’s no built-in replay or consumer offset mechanism.

3. **Payload size is capped (~8 KB)**
   You really shouldn’t be stuffing large payloads into the notification itself. The official docs explicitly recommend storing big data in a table and only sending a key. ([PostgreSQL][1])

4. **All listeners see all notifications**
   It’s pub/sub, not consumer groups. If you have multiple workers, each one gets the same notification and must coordinate in userland.

The pattern we want is:

> **Use LISTEN/NOTIFY as the “doorbell”, and a table as the durable queue.**

Let’s build that.

---

## Pattern #1: Durable Event Queues with Tables + LISTEN/NOTIFY

We’ll implement a minimal but production-grade event queue on top of Postgres primitives.

Conceptually:

-   **Producers** insert rows into an `event_outbox` table _inside_ their business transactions.
-   The same transaction also calls `pg_notify(...)`.
-   **Consumers**:

    -   `LISTEN` on a channel for wake-ups
    -   Pull rows from `event_outbox` using `FOR UPDATE SKIP LOCKED` to distribute work
    -   Mark events as processed

### Step 1: The Outbox Table

Start with a schema like this:

```sql
CREATE TABLE event_outbox (
    id           bigserial PRIMARY KEY,
    stream_name  text        NOT NULL, -- e.g. 'order'
    stream_key   text        NOT NULL, -- e.g. 'order:123'
    type         text        NOT NULL, -- e.g. 'order.created'
    payload      jsonb       NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz,
    -- optional metadata for locking & tracing
    locked_by    text,
    locked_at    timestamptz
);

CREATE INDEX ON event_outbox (processed_at, id);
CREATE INDEX ON event_outbox (stream_name, stream_key, id);
```

This table is your **durable log**:

-   `id` gives you global ordering
-   `stream_name + stream_key` let you reason about per-aggregate ordering
-   `processed_at` marks completion for a given consumer (we’ll start with a single consumer group)

### Step 2: Enqueue Function with NOTIFY

Next, write a helper function that inserts an event and notifies listeners.

```sql
CREATE OR REPLACE FUNCTION enqueue_event(
    p_stream_name text,
    p_stream_key  text,
    p_type        text,
    p_payload     jsonb
) RETURNS bigint AS $$
DECLARE
    v_id bigint;
BEGIN
    INSERT INTO event_outbox (stream_name, stream_key, type, payload)
    VALUES (p_stream_name, p_stream_key, p_type, p_payload)
    RETURNING id INTO v_id;

    -- Fire an async notification; listeners will see it after commit
    PERFORM pg_notify('event_outbox', v_id::text);

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
```

Because both the insert **and** `pg_notify` run inside your application transaction:

-   If the transaction commits, listeners see both the durable row and the notification.
-   If it rolls back, **neither** the row nor the notification exist.

This solves the classic “outbox problem” more cleanly than “write to DB, then send Kafka message in app code.” ([PostgreSQL][1])

### Step 3: Hook Into Your Domain Writes

Example: when an order is created, you want to emit an `order.created` event.

You might have something like:

```sql
CREATE TABLE orders (
    id          uuid PRIMARY KEY,
    customer_id uuid NOT NULL,
    total_cents integer NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
```

You can call `enqueue_event` in your application code after inserting the `orders` row **within the same transaction**, or use a trigger:

```sql
CREATE OR REPLACE FUNCTION orders_outbox_trigger()
RETURNS trigger AS $$
BEGIN
    PERFORM enqueue_event(
        'order',
        NEW.id::text,
        'order.created',
        to_jsonb(NEW)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER orders_outbox_after_insert
AFTER INSERT ON orders
FOR EACH ROW EXECUTE FUNCTION orders_outbox_trigger();
```

Now every new order automatically emits an event row and a notification.

### Step 4: A Worker That Listens and Drains

Let’s use `asyncpg` in Python (the same idea works in Go, Node, etc.). `asyncpg` exposes an `add_listener` method that registers a callback for Postgres notifications. ([yinternational.co.kr][7])

We’ll use:

-   One connection dedicated to `LISTEN`
-   Another connection (or pool) to pull and process events

```python
import asyncio
import asyncpg
import json
import os
from contextlib import asynccontextmanager

DSN = os.getenv("DATABASE_URL", "postgres://user:pass@localhost/appdb")

CHANNEL = "event_outbox"
CONSUMER_NAME = "worker-1"
BATCH_SIZE = 10


@asynccontextmanager
async def create_pool():
    pool = await asyncpg.create_pool(DSN, min_size=1, max_size=5)
    try:
        yield pool
    finally:
        await pool.close()


async def process_event(row):
    event_type = row["type"]
    payload = row["payload"]
    print(f"[{CONSUMER_NAME}] handling {event_type} id={row['id']}")
    # do your business logic here
    await asyncio.sleep(0.1)  # pretend work


async def drain_once(conn):
    rows = await conn.fetch(
        """
        UPDATE event_outbox
        SET locked_by = $1,
            locked_at = now()
        WHERE id IN (
            SELECT id
            FROM event_outbox
            WHERE processed_at IS NULL
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT $2
        )
        RETURNING id, type, payload
        """,
        CONSUMER_NAME,
        BATCH_SIZE,
    )

    if not rows:
        return False

    for row in rows:
        try:
            await process_event(row)
            await conn.execute(
                "UPDATE event_outbox SET processed_at = now() WHERE id = $1",
                row["id"],
            )
        except Exception as e:
            # In a real system you’d log and maybe move to a DLQ table
            print(f"Error processing event {row['id']}: {e}")

    return True


async def worker_loop(pool, wakeup_queue: asyncio.Queue):
    async with pool.acquire() as conn:
        while True:
            # Drain as long as there’s work
            while await drain_once(conn):
                pass

            # Sleep a bit or wait for the doorbell
            try:
                await asyncio.wait_for(wakeup_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                # periodic poll in case we missed a notification
                continue


async def listen_loop(wakeup_queue: asyncio.Queue):
    conn = await asyncpg.connect(DSN)
    await conn.execute(f"LISTEN {CHANNEL};")

    def _callback(connection, pid, channel, payload):
        # We don't care about which id specifically; just wake the worker
        wakeup_queue.put_nowait(None)

    await conn.add_listener(CHANNEL, _callback)
    print(f"Listening on channel {CHANNEL}...")

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await conn.close()


async def main():
    wakeup_queue = asyncio.Queue(maxsize=1000)

    async with create_pool() as pool:
        await asyncio.gather(
            listen_loop(wakeup_queue),
            worker_loop(pool, wakeup_queue),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

What this setup gives you:

-   **Low latency**: workers are woken up almost immediately by `NOTIFY`.
-   **Durability**: events live in `event_outbox` until marked processed.
-   **Backpressure**: if workers are slow, events simply accumulate in the table.
-   **Safe concurrency**: multiple workers can compete for events thanks to `FOR UPDATE SKIP LOCKED`, which is a standard Postgres pattern for job queues. ([PostgreSQL Korea][8])

If a worker dies mid-batch, the locks are released on transaction rollback and other workers can pick them up.

---

## Extending the Pattern: Consumer Groups & Retention

So far we’ve assumed a single logical consumer.

If you want _multiple independent_ consumer groups (e.g. `email-service`, `search-indexer`, `billing`), you have a few options:

1. **Per-consumer outbox tables**
   Each consumer gets its own `event_outbox_*` table & channel. Simple but more schema.

2. **Per-consumer “offset” table**
   Keep `event_outbox` as the central log, and track consumer positions in a separate table:

    ```sql
    CREATE TABLE event_consumer_offsets (
        consumer_name text PRIMARY KEY,
        last_seen_id  bigint NOT NULL
    );
    ```

    Workers then do:

    ```sql
    SELECT ...
    FROM event_outbox
    WHERE id > (SELECT last_seen_id FROM event_consumer_offsets WHERE consumer_name = $1)
    ORDER BY id
    LIMIT 100;
    ```

    Update `last_seen_id` as part of the same transaction when marking events processed.

3. **Hybrid**
   Use #2 for critical consumers, and “fire-and-forget” notifications for best-effort subscribers (e.g. metrics dashboards).

For **retention**, you can periodically delete old, fully processed events (e.g., where all consumer offsets are greater than `event_outbox.id`). For small systems, even a single `DELETE` or partition-based pruning job run nightly is plenty.

---

## Pattern #2: Postgres Logical Decoding as a Streaming Bus

The table + LISTEN/NOTIFY approach works great as an internal queue. But what if:

-   You want to stream changes into external systems (data warehouse, search index, another service)?
-   You’d like a more “log-like” API that doesn’t require polling the DB with ad-hoc queries?

Enter **logical decoding**.

Logical decoding is Postgres’s mechanism for turning the Write-Ahead Log (WAL)—the low-level stream of physical changes—into a stream of **logical change events** (insert/update/delete), consumable by external programs. ([PostgreSQL][2])

Under the hood:

-   You create a **logical replication slot**, which represents a named stream of WAL changes. ([PostgreSQL][9])
-   An **output plugin** decides how to format those changes (e.g., a JSON blob, SQL-like statements, etc.). Postgres ships with `pgoutput` and some example plugins; community plugins like `wal2json` are common. ([DEV Community][10])

### Enabling Logical Decoding

On the Postgres server, you need:

```conf
wal_level = logical
max_replication_slots = 4     # or more, depending on how many streams you need
max_wal_senders = 4
```

These are standard configuration knobs for logical replication and logical decoding. ([postgrespro.com][11])

After reloading Postgres, create a replication slot:

```sql
SELECT * FROM pg_create_logical_replication_slot('events_slot', 'pgoutput');
```

Or with `wal2json` if installed:

```sql
SELECT * FROM pg_create_logical_replication_slot('events_slot', 'wal2json');
```

Now you have a durable “cursor” into the WAL named `events_slot`.

### Streaming Changes Out

The Postgres distribution includes a helper CLI, `pg_recvlogical`, which can stream logical changes from a slot. ([PostgreSQL][12])

Example:

```bash
pg_recvlogical -d appdb \
  --slot=events_slot \
  --plugin=wal2json \
  --start -f -
```

You’ll see a JSON stream with inserts/updates/deletes as they commit.

In code, you’d usually:

-   Use a library that can open a replication connection
-   Consume changes from the slot
-   Persist your own “offsets” or simply let the replication slot track progress

Logical decoding gives you:

-   Ordering and durability tied directly to WAL
-   A **single source of truth** for all committed changes in specific tables
-   A natural foundation for **Change Data Capture (CDC)** pipelines ([blog.peerdb.io][13])

### Combining Outbox + Logical Decoding

A powerful pattern is:

1. Keep the **outbox table** as above.
2. Configure logical decoding to **only stream changes from that outbox table** (e.g., via publication filters or by letting your consumer filter rows by schema/table).
3. External services consume the WAL-based stream instead of polling.

This is effectively “Kafka, but stored in Postgres’s WAL”:

-   You still get atomic coupling between domain writes and outbox inserts.
-   Consumers read a forward-only append log.
-   You haven’t introduced another infra component yet.

Later, if you _do_ add Kafka, Debezium, etc., they can hang off the **same logical decoding feed** without changing the core app.

---

## When Is “Postgres as Message Bus” the Right Tool?

This approach works extremely well when:

-   You already have a **single Postgres cluster** that is the primary system of record.
-   Event throughput is moderate (hundreds or thousands of messages per second, not hundreds of thousands).
-   Most consumers are running in the same environment as the DB.
-   The most important property is **transactional correctness** between your domain state and emitted events.

You’ll likely be happy with:

-   LISTEN/NOTIFY + outbox table for internal workers
-   Optional logical decoding for streaming to a small number of external consumers

On the other hand, you probably want Kafka, Redpanda, Pulsar, NATS, etc. when:

-   You have **many independent consumer groups** with long-lived positions.
-   You need to store **months or years of event history** independent of your OLTP database.
-   There’s a strong requirement for cross-region, multi-datacenter event pipelines.
-   You’re approaching **very high throughput** and need specialized storage & compaction strategies.

Think of Postgres as your **small-systems event backbone**:

-   It’s simple.
-   It’s operationally friendly (one system instead of two).
-   It reuses the guarantees you already trust for your data.

And when you eventually outgrow it, you’ll have a clean path to plug in a dedicated message bus.

---

## Summary & Further Reading

We covered:

-   How `LISTEN`/`NOTIFY` gives you **low-latency pub/sub** inside Postgres, and why notifications alone aren’t a full queue. ([PostgreSQL][1])
-   Building a **durable event queue** using:

    -   An `event_outbox` table as the event log
    -   A PL/pgSQL `enqueue_event` function
    -   LISTEN/NOTIFY as a wake-up signal
    -   `FOR UPDATE SKIP LOCKED` to safely scale concurrent workers ([PostgreSQL Korea][8])

-   Using **logical decoding** to turn the WAL into a structured change stream that looks and feels like a message bus. ([PostgreSQL][2])

If you’re running a small or mid-sized system and you’re on the fence about adding Kafka “because that’s what everyone does,” try this first. There’s a good chance Postgres can be your message bus for quite a while.

### Recommended reading

-   Official PostgreSQL docs on:

    -   [`LISTEN`](https://www.postgresql.org/docs/current/sql-listen.html) & [`NOTIFY`](https://www.postgresql.org/docs/current/sql-notify.html) ([PostgreSQL][3])
    -   [Logical Decoding](https://www.postgresql.org/docs/current/logicaldecoding-explanation.html) & [Logical Decoding examples](https://www.postgresql.org/docs/current/logicaldecoding-example.html) ([PostgreSQL][9])

-   Guides on logical decoding & CDC in Postgres ([OpenSourceDB][14])
-   Articles demonstrating Postgres queues with `LISTEN`/`NOTIFY` and `SKIP LOCKED` ([PostgreSQL Korea][8])

If you’d like, we can take this further and design:

-   A full “event schema” for your domain
-   Per-consumer offset tracking
-   Migration strategy from this Postgres-based backbone to Kafka or another system later on.

[1]: https://www.postgresql.org/docs/current/sql-notify.html?utm_source=thinhdanggroup.github.io "PostgreSQL: Documentation: 18: NOTIFY"
[2]: https://www.postgresql.org/docs/current/logicaldecoding.html?utm_source=thinhdanggroup.github.io "PostgreSQL: Documentation: 18: Chapter 47. Logical Decoding"
[3]: https://www.postgresql.org/docs/current/sql-listen.html?utm_source=thinhdanggroup.github.io "PostgreSQL: Documentation: 18: LISTEN"
[4]: https://m-falcon.tistory.com/528?utm_source=thinhdanggroup.github.io "[PostgreSQL] Notify — Falcon"
[5]: https://postgrespro.com/docs/postgresql/current/sql-notify?utm_source=thinhdanggroup.github.io "PostgreSQL : Documentation: 17: NOTIFY : Postgres Professional"
[6]: https://www.compilenrun.com/docs/database/postgresql/postgresql-advanced-features/postgresql-listen-notify/?utm_source=thinhdanggroup.github.io "PostgreSQL LISTEN/NOTIFY - Real-time Notifications | Compile N Run"
[7]: https://yinternational.co.kr/%ED%8C%8C%EC%9D%B4%EC%8D%AC-postgresql-listen-notify%EC%99%80-asyncpg%EB%A1%9C-%EA%B5%AC%ED%98%84%ED%95%98%EB%8A%94-%EC%8B%A4%EC%8B%9C%EA%B0%84-%EC%9D%B4%EB%B2%A4%ED%8A%B8-%EC%B2%98%EB%A6%AC/?utm_source=thinhdanggroup.github.io "파이썬 PostgreSQL LISTEN NOTIFY와 asyncpg로 구현하는 실시간 이벤트 처리"
[8]: https://postgresql.kr/blog/pg_listen_notify.html?utm_source=thinhdanggroup.github.io "LISTEN & NOTIFY 명령으로 구현하는 비동기식 작업 - PostgreSQL"
[9]: https://www.postgresql.org/docs/current//logicaldecoding-explanation.html?utm_source=thinhdanggroup.github.io "PostgreSQL: Documentation: 17: 47.2. Logical Decoding Concepts"
[10]: https://dev.to/sequin/how-postgresql-logical-decoding-and-plugins-work-471m?utm_source=thinhdanggroup.github.io "How PostgreSQL logical decoding and plugins work"
[11]: https://postgrespro.com/docs/postgresql/current/logicaldecoding-example.html?utm_source=thinhdanggroup.github.io "PostgreSQL : Documentation: 17: 47.1. Logical Decoding Examples"
[12]: https://www.postgresql.org/docs/17//logicaldecoding-example.html?utm_source=thinhdanggroup.github.io "PostgreSQL: Documentation: 17: 47.1. Logical Decoding Examples"
[13]: https://blog.peerdb.io/five-tips-on-postgres-logical-decoding?utm_source=thinhdanggroup.github.io "Five tips on Postgres logical decoding - PeerDB Blog"
[14]: https://opensource-db.com/logical-decoding-and-logical-replication-in-postgresql/?utm_source=thinhdanggroup.github.io "Logical Decoding and Logical Replication in PostgreSQL"
