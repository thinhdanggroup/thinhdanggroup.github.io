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
    overlay_image: /assets/images/peerdb-subsecond-data-sync/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/peerdb-subsecond-data-sync/banner.png
title: "Achieving Sub‑Second Data Syncs: The Performance Engineering Behind PeerDB"
tags:
    - PeerDB
    - Sub-second Latency
    - Change Data Capture
    - PostgreSQL
---

_How do you move fresh data from PostgreSQL into analytics systems, queues, and storage engines in **hundreds of milliseconds**, not minutes? This post walks through the design choices and runtime tricks that make that possible in PeerDB, with concrete patterns you can borrow even if you’re building your own pipeline._

---

## Why sub‑second even matters

Dashboards feel “live” when they update within a second; fraud detection, inventory, and personalization engines often need new facts in that same ballpark. Anything slower becomes a batch. “Real‑time” is a spectrum, but users notice when changes take longer than a breath.

PeerDB’s stated focus is fast, Postgres‑first replication: log‑based CDC (change data capture), initial loads, and streaming into sinks like ClickHouse, Snowflake, BigQuery, Kafka, and others. The interesting part is how it squeezes latency while keeping correctness and operability sane. Architecturally, PeerDB separates **query/coordination** from **data movement** and leans on Temporal for orchestrating long‑running, idempotent workflows; it also keeps a Postgres “catalog” for metadata. In short: a layered system with a tight inner loop. ([PeerDB Docs][1])

PeerDB’s docs and ecosystem posts emphasize Postgres logical replication under the hood, pragmatic batching, and a bunch of Postgres‑native optimizations. They also report large‑throughput figures (e.g., ~30s average lag at 1k TPS in one benchmark) and “10× faster” claims over some tools—numbers that make sense once you see how the pipeline is shaped, but also remind us that _sub‑second_ is an SLO you earn per workload, not a universal constant. ([PeerDB Docs][2])

---

## The 500‑ms latency budget (from the data’s point of view)

Before we open the hood, let’s allocate half a second across the path a single change travels:

1. **Source commit → WAL visible** (0–10 ms): Postgres commits and writes to WAL; logical decoding exposes change records.
2. **WAL read → decode → micro‑batch** (5–50 ms): The replicator receives messages, decodes, and appends to a small batch.
3. **Network hop(s) to sink** (5–50 ms): TLS + serialization + transit.
4. **Apply at sink** (10–200 ms): Convert to sink schema, write/flush.
5. **Ack → advance LSN watermarks** (1–10 ms): Confirm durably applied.

The “apply” step dominates. So sub‑second is really a story about **efficient decoding and **tiny, well‑formed writes\*\* to your sink—plus ruthless avoidance of head‑of‑line blocking.

---

## The shape of PeerDB

At a high level (paraphrasing docs terminology):

-   **Nexus Query Layer (Rust):** Postgres‑compatible SQL interface (PGWire) that lets you define peers, mirrors, and run control queries. Horizontally scalable.
-   **Flow (Go):** The data plane—API + workers that move bytes from sources to sinks.
-   **Temporal:** Orchestrates long‑running, retryable, idempotent flows.
-   **Catalog (Postgres):** Stores configuration and workflow state. ([PeerDB Docs][1])

This split is crucial: keep the **control path** (SQL/metadata orchestration) separate from the **data path** (tight loops doing I/O). Temporal provides durable state for “did we already apply chunk N?”, backoffs, and compensation—without polluting the hot path with heavy coordination logic. ([blog.peerdb.io][3])

---

## From WAL to rows: decoding fast without tripping

PeerDB consumes **logical replication** from a Postgres slot. You can imagine a loop like this (Go‑flavored pseudocode):

```go
// Pseudocode: hot path of a WAL reader and micro-batcher
func streamSlot(ctx context.Context, slot Slot, sink Sink) error {
    r := NewLogicalReplicationConn(slot)
    defer r.Close()

    // Track watermarks to ensure exactly-once delivery.
    var lastFlushedLSN LSN

    batch := make([]Change, 0, 1024)
    ticker := time.NewTicker(5 * time.Millisecond) // time-based flush
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()

        default:
            msg, lsn, err := r.ReadMessage(ctx)
            if err == ErrNoMessage {
                // Heartbeat/ack to keep WAL retention sane.
                _ = r.AckStandbyStatus(lastFlushedLSN)
                continue
            }
            if err != nil { return err }

            change := decodeLogical(msg) // fast path: no allocations, reuse buffers
            batch = append(batch, change)

            // Flush on size or time threshold (micro-batching).
            if len(batch) >= 1024 { // size-based
                lastFlushedLSN = flushBatch(ctx, sink, batch, lsn)
                batch = batch[:0]
            }

            select {
            case <-ticker.C:
                if len(batch) > 0 {
                    lastFlushedLSN = flushBatch(ctx, sink, batch, lsn)
                    batch = batch[:0]
                }
            default:
            }
        }
    }
}
```

**Design notes:**

-   **Micro‑batches** (size/time) amortize per‑record overhead while keeping tail latency bounded. A 5–10 ms timer keeps the pipeline “breathing” even at low throughput.
-   **Zero/low copy**: decode using reusable buffers; avoid per‑row heap allocations.
-   **Watermarks**: track the **last durably applied LSN**; only then ack to Postgres (advancing WAL retention).
-   **Heartbeats**: send `standby_status_update` even when idle so Postgres doesn’t hoard WAL files.

The Postgres side needs sane CDC configs (e.g., `wal_level=logical`, enough `max_replication_slots/wal_senders`, WAL retention policies, etc.). PeerDB’s tuning guides describe slot consumption behaviors and timeouts; the exact thresholds you pick translate directly into e2e latency. ([PeerDB Docs][4])

---

## Cutting over cleanly: snapshot + CDC bridge

Real systems start with a big table that already has data. Fast initial load is step one; then you **bridge** to CDC at a specific LSN so you don’t miss or duplicate rows. PeerDB’s CDC setup explicitly does this: full load first, then tail the WAL and apply changes. The trick is choosing a cutover LSN and ensuring all snapshot rows ≤ LSN are loaded **before** you apply deltas > LSN. ([PeerDB Docs][5])

A robust recipe is:

1. Open a repeatable‑read transaction and **record the current LSN** (`pg_current_wal_lsn()`).
2. Snapshot the table(s) in **parallel chunks** under that transaction snapshot (so you see a consistent view).
3. Start CDC from the recorded LSN; ignore rows ≤ LSN (already in the snapshot), apply > LSN.

Sketch:

```sql
-- Step 1: in a REPEATABLE READ txn
SELECT pg_export_snapshot();           -- shareable snapshot id
SELECT pg_current_wal_lsn();           -- cutover LSN

-- Step 2: workers use the exported snapshot
SET TRANSACTION SNAPSHOT '...';
-- Each worker pulls a chunk (by PK ranges or logical partitions)
SELECT * FROM my_table
 WHERE id BETWEEN $chunk_min AND $chunk_max;

-- Step 3: begin CDC from cutover_lsn
-- The CDC reader discards messages whose commit_lsn <= cutover_lsn.
```

On large tables, **chunking strategy** matters: pick boundaries by clustered PKs or synthetic ranges that preserve locality, and watch out for hotspots. PeerDB literature often highlights parallelized initial load with consistency guarantees; that’s a big contributor to slashing hours → minutes on day‑one syncs. ([GitHub][6])

---

## The writer’s job: columnar‑friendly, idempotent, and quick to flush

Sink‑side performance determines your tail latency. Whether you’re writing to ClickHouse, Snowflake, BigQuery, or a queue, the same patterns apply:

1. **Map schema once** (and cache): keep a compiled plan for type conversions, especially for JSONB, arrays, and wide rows.
2. **Columnar staging** (for OLAP sinks): group rows into column vectors and write via the sink’s native bulk path.
3. **Idempotency keys**: use a deterministic key per change (e.g., `{table, primary_key, commit_lsn, op_index}`) so retried writes don’t duplicate.

Minimal Go‑like pseudocode for an idempotent writer:

```go
func flushBatch(ctx context.Context, sink Sink, batch []Change, uptoLSN LSN) LSN {
    // 1) Transform to sink layout (avoid per-row reflection; use compiled mappers)
    colset := toColumnar(batch)

    // 2) Idempotent write: sink ensures dedupe by (table, pk, commit_lsn, op_idx)
    // For warehouses, implement as a staging table + MERGE/INSERT ON CONFLICT.
    if err := sink.Write(ctx, colset, WithIdempotency()); err != nil {
        // Let Temporal retry at the activity level (see next section).
        panic(err) // bubble up; orchestration handles backoff + replay
    }

    // 3) Report watermark: uptoLSN is safe to ack upstream
    return uptoLSN
}
```

When the sink is **ClickHouse**, the fastest path is usually staging (or streaming) with a small, compressed batch on a few columns, then letting ClickHouse’s insert pipeline do the rest. PeerDB documentation and partner blogs emphasize this path and the focus on Postgres‑centric optimizations (e.g., TOAST column handling, schema change propagation). Those “sharp edges” are where end‑to‑end latency is often lost. ([ClickHouse][7])

---

## Temporal, retries, and exactly‑once semantics (without blocking the hot path)

CDC code must be **idempotent** and **retryable**. PeerDB uses **Temporal** to orchestrate long‑running workflows and manage retry policies, backoff, and state transitions—essential when copying billions of rows or keeping a mirror alive across failures. Temporal lets the hot loop crash and be replayed deterministically at an activity boundary, with dedup baked in. ([blog.peerdb.io][3])

A simplified Temporal workflow (Go SDK flavor):

```go
// Workflow coordinates snapshot + CDC and tracks watermarks.
func MirrorWorkflow(ctx workflow.Context, cfg MirrorConfig) error {
    // Activities are the units that can fail/retry/idempotently resume.
    ao := workflow.ActivityOptions{
        StartToCloseTimeout: time.Hour,
        RetryPolicy: &temporal.RetryPolicy{
            InitialInterval: time.Second,
            MaximumInterval: time.Minute,
            MaximumAttempts: 0, // unlimited
        },
    }
    ctx = workflow.WithActivityOptions(ctx, ao)

    var cutoverLSN LSN
    if err := workflow.ExecuteActivity(ctx, SnapshotAll, cfg).Get(ctx, nil); err != nil {
        return err
    }
    if err := workflow.ExecuteActivity(ctx, GetCutoverLSN, cfg).Get(ctx, &cutoverLSN); err != nil {
        return err
    }
    // CDC runs "forever"; Temporal keeps durable state (last applied LSN).
    return workflow.ExecuteActivity(ctx, TailCDC, cfg, cutoverLSN).Get(ctx, nil)
}

// Activity TailCDC uses idempotent writes; on retry, it resumes from last durable LSN.
```

The big win here is **separation of concerns**: the activity (reader/writer loop) is simple and fast; the workflow remembers where you left off, handles operator‑friendly pauses/resumes, and enforces idempotency. ([blog.peerdb.io][3])

---

## Dynamic batching: riding the sweet spot between latency and throughput

Batch too small and you drown in per‑row overhead; batch too large and you’ll see multi‑second flushes and long tail latency. A resilient heuristic:

```python
# Pseudocode for adaptive batch sizing around a target p95 latency
target_ms = 200  # target sink-apply time per batch
min_rows, max_rows = 50, 5000
rows = 250

def on_flush(measured_ms):
    global rows
    if measured_ms < target_ms * 0.6 and rows < max_rows:
        rows = int(rows * 1.5)      # be bolder
    elif measured_ms > target_ms * 1.2 and rows > min_rows:
        rows = max(min_rows, rows // 2)  # back off quickly
```

This simple controller keeps steady‑state batches near the “knee” of your sink’s latency curve while preventing sudden spikes from cascading into timeouts. Keep a **time‑based cap** (e.g., flush in 5–10 ms even if rows are few) to maintain sub‑second SLOs during lulls.

---

## Backpressure without meltdowns

Two backpressures matter:

1. **Upstream (Postgres):** If the sink slows, you must **not** ack beyond what’s durably applied. WAL files will accumulate until retention limits bite. Keep alerts on `pg_stat_replication` lag and set WAL retention to tolerate a realistic outage window.
2. **Downstream (sink):** If merges/flushes slow, shrink batches and possibly **pause** specific tables (not the whole mirror). PeerDB exposes pause/edit/resync features and documents behaviors around slot consumption; build similar controls if you’re rolling your own. ([PeerDB Docs][1])

A handy instrumentation pattern is to track and export three watermarks:

-   **`source_commit_lsn`** (what the app committed),
-   **`read_lsn`** (what the reader has fetched),
-   **`applied_lsn`** (what’s fully written downstream).

The deltas are your **ingest lag** and **apply lag**. If read ≫ applied, the sink is the bottleneck; if commit ≫ read, the reader or network is. Throw these on a graph; your on‑call will thank you.

---

## Schema evolution: handling DDL without stalling

In practice, many pipelines fall over when someone adds a column. Robust CDC needs to:

-   **Capture DDL** events (at least the ones that affect your mirrored tables),
-   **Regenerate** mapping plans quickly (no hours‑long manual reconfig),
-   Handle **TOAST** columns (large values) efficiently.

PeerDB highlights support for schema changes and efficient TOAST streaming as table‑stakes for Postgres‑first CDC. Your writer should tolerate “extra” columns (forward‑compatible) and fill defaults when applying to sinks that lag a DDL. ([GitHub][6])

---

## Cursor‑based vs log‑based flows

Not every source supports logical replication. Cursor‑based (timestamp/integer) or `xmin`‑based incremental reads are still useful—and typically run on a **refresh interval** rather than an always‑on stream. In PeerDB, mirrors expose a `refresh_interval` (seconds) for those poll‑driven modes; it defaults to ~10s. That’s perfect for cost‑sensitive tables and still “near real‑time,” but it won’t hit sub‑second. Reserve the sub‑second budget for true CDC. ([PeerDB Docs][8])

---

## The concurrency model: simple workers, hot loops, and cooperative yielding

For the hot loop, you want **predictable latency** more than theoretical peak throughput. A few playbook items:

-   **Pin CPU‑heavy stages** (decode, transform) to cores; leave I/O async.
-   **Cooperative design**: keep units of work small (≤ a few ms) and yield—similar to how CPython’s interpreter checks for signals and periodically releases the GIL to keep the VM responsive under mixed workloads. Your goal is the same: avoid monolithic, long‑running sections that cause **tail‑latency spikes**.
-   **Memory discipline**: pre‑allocate buffers; recycle slices/vectors; shun per‑record heap allocation. This is the CDC equivalent of CPython’s small‑object allocator: predictable, amortized costs beat fancy pools that fragment over time.

The surprisingly pragmatic rule: **keep the hot path boring**. Push complexity (retries, backoffs, compaction, checksums, exactly‑once semantics) to the orchestration layer (Temporal) and to **activity boundaries** that can fail/retry.

---

## Observability: don’t guess—measure

Sub‑second SLOs die quietly without visibility. Minimal dashboards:

-   **p50/p90/p99 apply time** per sink (batch latency),
-   **E2E event age** percentiles (`now - change.commit_time`),
-   **Watermarks** (commit vs read vs applied LSNs),
-   **Batch size dynamics** (so you see the controller’s decisions),
-   **WAL retained bytes** (so you don’t learn about retention the hard way).

Alert on **trends** (derivatives), not just absolutes: “apply p99 increased 3× over 10m” beats a static 1s threshold.

---

## Practical tuning checklist for sub‑second targets

**On the source (Postgres):**

-   `wal_level=logical`, tune `max_replication_slots`, `max_wal_senders`.
-   WAL retention sized for your **RTO** (how long can the sink be down?).
-   Avoid super‑high `synchronous_commit` settings unless you _need_ sync semantics; CDC does not require it.
-   Create **logical publications** narrowly scoped to the tables you actually mirror.
-   Index your primary keys (obvious, but…).

**On the pipeline:**

-   Keep **micro‑batches** small (50–5000 rows) with **5–10 ms** time caps.
-   Tune compression and row/columnar conversion for your sink.
-   **Adaptive batch sizing** around a target write‑time (see controller code above).
-   Make idempotency keys deterministic from `{table, pk, LSN, op_idx}`.
-   Consider **staging tables** + `MERGE`/`INSERT ON CONFLICT` for dedupe.

**On the sink:**

-   Prefer the **native bulk path** (e.g., ClickHouse native protocol / columnar insert) over ad‑hoc row‑by‑row writes.
-   Pre‑create tables with correct types; avoid implicit casts on every insert.
-   Separate ingestion from heavy queries (resource groups, throttles) to avoid self‑inflicted backpressure.

---

## Real‑world wrinkles (and how to smooth them)

-   **Burstiness:** Evening jobs can unleash millions of changes. The adaptive controller will stretch batch sizes; consider temporary **fan‑out** (more workers) and ensure WAL retention can carry you through.
-   **DDL storms:** Instead of pausing everything on DDL detection, _buffer_ changes for the impacted table briefly, apply the DDL downstream, then drain the buffer.
-   **Network partitions:** Let the Temporal workflow park the mirror gracefully when sink timeouts grow beyond a budget; on resume, pick up from the **applied LSN**. ([blog.peerdb.io][3])
-   **Large objects/TOAST:** Chunk and stream efficiently; prefer **patch‑style** updates when the sink supports it, otherwise expect bigger batches and longer apply times. ([GitHub][6])

---

## A note on expectations: sub‑second vs. tens of seconds

You _can_ get sub‑second e2e for many operational tables—especially those with modest write rates and sinks optimized for ingestion. Under heavy, sustained write loads (thousands of TPS) to wide rows or JSONB blobs, the realistic target may be “a few seconds” or “tens of seconds.” PeerDB’s public benchmarks call out ~30 s lag around 1k TPS as a baseline point of reference. Treat sub‑second as a **tiered SLO**: apply it to the most critical tables/changes; let others breathe. ([PeerDB Docs][2])

---

## Putting it together: a “minimal PeerDB‑style” mirror in ~50 lines of logic

Here’s a bite‑sized, language‑agnostic outline you can adapt:

1. **Discover & plan:** Resolve table schemas and build a mapping plan (source→sink types).
2. **Snapshot phase:** Export a snapshot, record cutover LSN, parallel‑scan chunks under the exported snapshot, write via sink’s bulk path.
3. **Start CDC:** Begin logical replication from the cutover LSN; decode messages into a ring buffer.
4. **Micro‑batch & write:** Every 5–10 ms or N rows, transform→write→commit; on success, advance the applied LSN.
5. **Ack upstream:** Periodically send `standby_status_update(applied_lsn)`.
6. **Adaptive control:** Adjust batch size based on measured apply time.
7. **Orchestrate:** Wrap 2–6 in an idempotent workflow with retries and durable state (Temporal).

That’s the essence of the “sub‑second mindset”: _keep the hot path hot, the slow path observable, and the whole thing restartable at any boundary_.

---

## What PeerDB specifically brings to the table

A lot of the above is generic CDC wisdom, but PeerDB’s public materials highlight several practical strengths that make hitting tight SLOs less painful:

-   **Postgres‑first optimizations** (logical slot reading, parallel snapshotting, TOAST handling, schema propagation). ([GitHub][6])
-   **Natively Postgres‑flavored control surface** (PGWire SQL via the Nexus layer), making ETL feel like DDL/DML you already know. ([PeerDB Docs][1])
-   **Temporal‑backed orchestration** for retries, idempotency, and long‑running syncs without bespoke state machines. ([blog.peerdb.io][3])
-   **ClickHouse‑first path** for low‑latency analytics ingestion, now even offered natively in ClickHouse Cloud. ([ClickHouse][7])
-   **Multiple modes** beyond CDC (cursor/xmin), with explicit refresh intervals—useful when you want near‑real‑time without the constant read. ([PeerDB Docs][8])

---

## Summary: design principles for sub‑second data syncs

-   **Treat time as a resource.** Micro‑batch on size **and** time; keep 5–10 ms heartbeats in the loop.
-   **Bridge snapshot to CDC with a recorded LSN.** Consistency first; speed follows. ([PeerDB Docs][5])
-   **Write the way your sink wants to be written to.** Columnar where possible, minimal type coercion, idempotent upserts.
-   **Move orchestration out of the hot path.** Use a workflow engine (Temporal) for retries and durable progress. ([blog.peerdb.io][3])
-   **Close the loop with adaptive control and metrics.** Autotune batch size; graph watermarks and p99s; alert on trends.
-   **Plan for evolution.** DDL, schema drift, TOAST, and bursts are normal; make them boring.

If you’re building your own pipeline, you can steal these patterns wholesale. If you’re shopping, the public architecture around PeerDB shows a sensible and proven shape for cutting latency without sacrificing operability.

---

## Further reading

-   **PeerDB Architecture Overview** – Nexus (Rust), Flow (Go), Temporal, and catalog database. ([PeerDB Docs][1])
-   **Using Temporal to Scale Data Synchronization at PeerDB** – how orchestration underpins retries, idempotency, and long‑running workflows. ([blog.peerdb.io][3])
-   **Real‑time CDC Overview & Benchmarks** – reported “10× faster” claims and lag at 1k TPS. ([PeerDB Docs][2])
-   **ClickHouse welcomes PeerDB** – context on the ClickHouse integration path for low‑latency analytics. ([ClickHouse][7])
-   **CDC tuning notes** – slot consumption behavior and config pointers. ([PeerDB Docs][4])

_If you want the gory, line‑by‑line details, open the source and docs. But even if you never deploy PeerDB, internalizing these loops and budgets is the shortest path to replica freshness that feels instantaneous to your users._

[1]: https://docs.peerdb.io/architecture "Architecture Overview - PeerDB Docs: Setup your ETL in minutes with SQL."
[2]: https://docs.peerdb.io/usecases/Real-time%20CDC/overview?utm_source=thinhdanggroup.github.io "Overview - PeerDB Docs: Setup your ETL in minutes with SQL."
[3]: https://blog.peerdb.io/using-temporal-to-scale-data-synchronization-at-peerdb?utm_source=thinhdanggroup.github.io "Using Temporal to Scale Data Synchronization at PeerDB"
[4]: https://docs.peerdb.io/metrics/important_cdc_configs?utm_source=thinhdanggroup.github.io "Config Tuning for Change Data Capture (CDC) - PeerDB Docs: Setup your ..."
[5]: https://docs.peerdb.io/mirror/cdc-pg-pg?utm_source=thinhdanggroup.github.io "CDC Setup from Postgres to Postgres - PeerDB Docs: Setup your ETL in ..."
[6]: https://github.com/PeerDB-io/peerdb?utm_source=thinhdanggroup.github.io "GitHub - PeerDB-io/peerdb: Fast, Simple and a cost effective tool to ..."
[7]: https://clickhouse.com/blog/clickhouse-welcomes-peerdb-adding-the-fastest-postgres-cdc-to-the-fastest-olap-database?utm_source=thinhdanggroup.github.io "ClickHouse welcomes PeerDB: Adding the fastest Postgres CDC to the ..."
[8]: https://docs.peerdb.io/sql/commands/create-mirror?utm_source=thinhdanggroup.github.io "Creating Mirrors - PeerDB Docs: Setup your ETL in minutes with SQL."
