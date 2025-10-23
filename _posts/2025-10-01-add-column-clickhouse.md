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
    overlay_image: /assets/images/livekit-dashboard/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/livekit-dashboard/banner.png
title: "Adding a Column in ClickHouse, Deeply: What Actually Happens and What to Consider"
tags:
    - ClickHouse
---

_“It’s just one more column.”_
Famous last words.

If you use ClickHouse long enough, you’ll eventually need to add a column to a big, busy table. Maybe product wants a new flag, maybe you forgot to log a correlation ID, or maybe you’re mid-migration and need a transitional field. In a row-store, adding a column often smells like a table rewrite. In ClickHouse, it’s different—and wonderfully so—but there are still sharp edges worth understanding.

This post walks through **how adding a column works under the hood in ClickHouse**, the **options you have**, and the **gotchas to consider** when doing this on real, high-throughput clusters. We’ll start with mental models, drop to storage-engine details, then climb back up to practical checklists and patterns.

---

## TL;DR (But Please Don’t)

-   **Adding a column to a `MergeTree` table is metadata-only and fast.** Existing parts are not rewritten immediately. Reads synthesize the new column for old parts using its default.
-   **You choose when (or if) to physically backfill.** Leave it virtual forever (cheap for constants), or materialize later via merges/mutations if the default is non-constant or you want full on-disk data.
-   **Replicated clusters propagate the ALTER.** Use `ON CLUSTER` to keep schemas in lockstep across shards/replicas.
-   **Design for compatibility:** prefer `Nullable(...)` for transitional changes, be careful with `MATERIALIZED`/`ALIAS`, and think about downstream materialized views and ingestion pipelines.
-   **Operationally:** watch mutation backlogs, disk I/O, and merges if you choose to materialize; test on one shard; plan codecs and indices intentionally.

Okay—now the fun version with the why.

---

## A Mental Model: Parts, Not Pages

ClickHouse’s `MergeTree` family stores data in **parts**: immutable columnar chunks on disk. Inserts create new parts; background merges compact them. Each part is self-describing (it has its own columns, indexes, checksums). Reads stitch together results across parts and across columns.

When you run:

```sql
ALTER TABLE events ADD COLUMN request_id UUID DEFAULT generateUUIDv4();
```

ClickHouse **does not** open every part and append a column. It simply updates the table metadata. From that point on:

-   **New parts** written after the ALTER **will include** the `request_id` column physically (materialized on insert).
-   **Old parts** do **not** contain `request_id`. When a query touches those parts and asks for `request_id`, ClickHouse **synthesizes** the value using the column’s default expression. No files changed.

This is the core reason `ADD COLUMN` is fast and online: it doesn’t rewrite history unless you ask it to.

---

## What “Default” Really Means Here

In ClickHouse, a column can have:

-   **No explicit default** – the engine uses the **type’s default value**: `0`/`0.0` for numbers, `''` for strings, `1970-01-01` for `Date`, `0000-00-00 00:00:00` for `DateTime`, empty arrays/maps, `false` for `Bool`, and `NULL` for `Nullable(T)`.
-   **`DEFAULT <expr>`** – an expression evaluated on insert and, for **missing data in old parts**, also evaluated at read time.
-   **`MATERIALIZED <expr>`** – computed and stored; you can’t insert into it directly.
-   **`ALIAS <expr>`** – virtual; never stored; always computed on read.

**Key implication:**
When you **add** a column to an existing table, any **old parts** that predate the change don’t have the column’s files. If the column is:

-   A **constant default** (e.g., `DEFAULT 0`, `DEFAULT 'unknown'`), ClickHouse can synthesize it cheaply on read: it literally behaves like a column filled with that constant for old parts.
-   A **non-constant expression** (e.g., `DEFAULT cityHash64(user_id)`), ClickHouse computes it per row for old parts. That’s CPU at query time. You can later **materialize** to push that CPU to the background once.

---

## What Actually Happens On Disk

Let’s peek at the lifecycle:

1. **Before ALTER**:
   Parts on disk contain files like `user_id.bin`, `user_id.mrk3`, `ts.bin`, `ts.mrk3`, etc.

2. **Run `ADD COLUMN`**:

    - ClickHouse updates table metadata (`columns.txt` in the table metadata path and in system tables).
    - No old part files are touched.

3. **New Inserts**:

    - Insert paths and materialized views now see the new column in the schema. If you include it in INSERT, your value is stored. If not, the default expression runs, and the column’s files are written for the **new part** being created.

4. **Reads**:

    - For **new parts**: data is loaded from the new column’s files.
    - For **old parts**: the column is missing; ClickHouse plugs in the default at read time (constant fast-path if applicable).

5. **Merges** (optional impact):

    - During background merges, if the column has a **non-constant default** or is `MATERIALIZED`, ClickHouse may materialize it into the merged part (engine/version dependent). If the default is a constant, many deployments happily leave it virtual forever; materializing doesn’t improve correctness.

6. **Explicit Materialization** (your call):
   You can force backfill via a mutation:

    ```sql
    -- Force materialization for all existing rows
    ALTER TABLE events UPDATE request_id = request_id WHERE 1;
    -- or, if you added a DEFAULT and want it baked in:
    ALTER TABLE events MATERIALIZE COLUMN request_id;  -- engine-version dependent syntax
    ```

    This creates **new parts** with the column physically present, replacing old parts as the mutation completes. It’s I/O and CPU heavy—plan it.

> Tip: Leave constant defaults virtual for a while (or forever) if you don’t need the column physically. It often saves a lot of churn.

---

## Schema Placement: `AFTER` and Logical Order

ClickHouse lets you control logical order:

```sql
ALTER TABLE events
  ADD COLUMN request_id UUID DEFAULT generateUUIDv4()
  AFTER user_id;
```

This **does not** rewrite old parts either. Column order mostly affects:

-   `SELECT *` output order,
-   How you (humans) read `DESCRIBE TABLE`,
-   Insert formats like CSV without headers (be explicit instead!).

On disk, ClickHouse stores columns independently. Order is a metadata concern.

---

## Types, Nullability, and Safety for Rolling Changes

Choose types with operational safety in mind:

-   **Prefer `Nullable(T)`** for additive fields when producers/consumers will roll out over time.

    -   Old writers unaware of the column can keep inserting; the default for `Nullable(T)` is `NULL`.
    -   New readers can check `col IS NULL` to distinguish missing historical values from real ones.

-   **Use `DEFAULT` values** carefully.

    -   If you choose a sentinel (e.g., `DEFAULT 0`), be sure that value has unambiguous semantics. With `Nullable`, the sentinel can be `NULL` instead of overloading `0`.

-   **`LowCardinality(String)`** is great for new enumerated fields. Combine with a constant default for cheap reads on old parts.

-   **Compression codecs**: define them at add time if you have strong preferences.

    ```sql
    ALTER TABLE events
      ADD COLUMN feature_flag LowCardinality(String)
      DEFAULT ''
      CODEC(ZSTD(3));
    ```

    You can change codecs later, but that requires a rewrite (mutation) to take full effect.

---

## Replication & Distributed Topologies

Adding a column in a replicated/sharded environment requires a little choreography.

### Replicated Tables

For `ReplicatedMergeTree` engines:

-   The `ALTER` is **replicated**: it’s recorded in ZooKeeper/ClickHouseKeeper and executed in order on each replica.
-   Existing data on each replica behaves the same way: old parts synthesize the column on read.

### Distributed Tables

For `Distributed` tables:

-   `Distributed` itself holds **no data** (just a local schema and the routing settings).

-   You must ensure **underlying shard tables** have the same schema. Use:

    ```sql
    ALTER TABLE shard_db.events ON CLUSTER my_cluster
      ADD COLUMN request_id UUID DEFAULT generateUUIDv4();
    ```

-   Then, optionally, **update the `Distributed` table** schema (so `DESCRIBE` reflects it locally). With recent versions, `ON CLUSTER` ensures uniformity across all hosts.

**Operational tip:** If you run blue/green clusters or have heterogeneous versions, test the `ALTER` on a canary shard first. Ensure materialized views and ingestion pipelines don’t explode when the new column appears.

---

## Materialized Views, Projections, and Secondary Indexes

Schema changes often ripple into acceleration structures.

### Materialized Views (MVs)

-   If an MV’s `SELECT` references `*`, a new source column may land in the target—sometimes good, sometimes not.
-   If an MV’s `SELECT` lists columns explicitly, it won’t automatically include the new column. You may need to **ALTER the target table** and **update the view** if you want to propagate it.
-   If you **add a column with `MATERIALIZED`** expression in the **source**, remember: you can’t insert into it, but it **will** be computed for new rows. Old rows remain virtual unless you materialize.

### Projections

-   Projections are like per-table materialized layouts. If the new column is **used in queries** that hit a projection, consider:

    -   **Add the column**, then
    -   **`ALTER TABLE ... MATERIALIZE PROJECTION`** to refresh or rebuild the projection so it includes the column.

### Data-Skipping Indexes

You can add secondary indexes that reference the new column:

```sql
ALTER TABLE events
  ADD COLUMN user_tier LowCardinality(String) DEFAULT ''
  AFTER user_id;

ALTER TABLE events
  ADD INDEX idx_tier user_tier TYPE set(0) GRANULARITY 1;  -- example index

ALTER TABLE events MATERIALIZE INDEX idx_tier;
```

The index definition is metadata; **`MATERIALIZE INDEX`** builds it for existing parts. This is a rewrite (background mutation), so account for CPU/I/O.

---

## Performance: When to Materialize vs. Stay Virtual

**Rule of thumb:**

-   If your default is **constant** (e.g., `DEFAULT 0`, `DEFAULT ''`, or `DEFAULT toDate('1970-01-01')`), **don’t rush** to materialize. ClickHouse can produce a constant column for old parts efficiently.
-   If your default is **computed per row** (e.g., hashing another column, parsing JSON, arithmetic), and queries frequently select/filter on it, **consider materializing**:

    -   Short-term: leave it virtual until the change stabilizes (no rollbacks), observe CPU impact.
    -   Medium-term: schedule a mutation off-hours to materialize.
    -   Long-term: rely on merges to gradually materialize if your version/settings do so—and if the pace is acceptable.

**Measuring impact:**

-   Compare query profiles before/after with `system.query_log` CPU and read rows for representative queries that reference the new column.
-   Watch `system.mutations` for progress (if you materialize) and `system.disks` for free space. Mutations need headroom.

---

## Safety Patterns for Rolling Releases

You rarely change only the database. Producers (writers), consumers (readers), ETL jobs, and dashboards all have opinions.

A battle-tested rollout plan:

1. **Add a `Nullable` column with a safe default.**

    ```sql
    ALTER TABLE events
      ADD COLUMN request_id Nullable(UUID);  -- default is NULL
    ```

2. **Update readers first** to tolerate `NULL` and prefer the new column if present:

    - `SELECT coalesce(request_id, old_request_id) AS request_id ...`
    - Or, if new logic depends on the column, guard it: `WHERE request_id IS NOT NULL`.

3. **Update writers** to start filling the column.

4. **(Optional) Backfill** historical data (if needed for analytics or joins). For very large tables, stage it:

    - Backfill hot partitions first (recent months).
    - Use `WHERE` ranges to limit mutation scope:

        ```sql
        ALTER TABLE events
          UPDATE request_id = generateUUIDv4()
          WHERE ts >= toDate('2025-01-01') AND request_id IS NULL;
        ```

5. **(Optional) Tighten the type** later:

    - If you no longer need `NULL`, you can `MODIFY COLUMN` to non-nullable once all data is filled and apps no longer write `NULL`.
    - This is a rewrite; plan it.

6. **(Optional) Add indexes/projections** once the column’s query patterns are clear.

---

## Failure Modes & Gotchas

Let’s list the traps so you can step around them:

-   **Downstream ingestion breaks:**
    Kafka engines, `INSERT SELECT` jobs, or external loaders that use `INSERT INTO table VALUES (...)` without column lists may misalign values once a new column appears. Always prefer `INSERT INTO table (col1, col2, ...) VALUES ...`.

-   **Materialized Views with strict schema:**
    If an MV’s target table doesn’t have the new column, and your `SELECT *` in the MV implicitly pulls it, the insert into the target can fail. Either pin the view’s select list or evolve the target in sync.

-   **Non-deterministic defaults:**
    `DEFAULT now()` or `generateUUIDv4()` is evaluated **per insert** (for new rows) and **per read** (for old parts) unless you materialize. That means **old rows will “change” over time** if you query them repeatedly using `now()` as a default. Avoid non-deterministic defaults for added columns unless you materialize immediately.

-   **Expression cost at read time:**
    `DEFAULT complex_json_extract(payload)` across billions of historical rows can be expensive. Either keep the column out of hot queries until materialized or schedule a staged backfill.

-   **Disk space during mutations:**
    Backfills create new parts alongside old ones until the mutation commits. Ensure enough free space (rule of thumb: > 2× the data volume you’ll rewrite for safety). Use partitioned `WHERE` clauses to control scope.

-   **Codec mismatch expectations:**
    Adding a column with a codec doesn’t retroactively change old parts (they don’t have the column yet). After materialization, your chosen codec applies to new/rewritten parts only.

-   **`ALIAS` isn’t stored:**
    Great for derived values, but if you expect to filter heavily on it, remember you’re always computing on read. For heavy workloads, prefer a real stored column with `MATERIALIZED` and materialize backfill.

-   **`AFTER` doesn’t “reorder” old parts:**
    It’s for logical order; nothing performance-critical changes.

-   **Distributed schema drift:**
    If one shard doesn’t receive the `ALTER`, queries via the `Distributed` table can fail with schema mismatch errors. Use `ON CLUSTER` and monitor.

---

## Practical Walkthrough

Let’s simulate a common scenario: add a request correlation ID to a hot `events` table.

### 1) Inspect

```sql
DESCRIBE TABLE events;
SELECT
  partition,
  name,
  active,
  rows
FROM system.parts
WHERE database = currentDatabase() AND table = 'events' AND active;
```

Know your partitions, row counts, and disk headroom before you do anything.

### 2) Add the Column (Safe First)

```sql
ALTER TABLE events
  ADD COLUMN request_id Nullable(UUID);
```

Instant. No rewrite. Existing queries that don’t reference `request_id` are unaffected.

### 3) Roll Out Writers

Application producers start sending `request_id` on new inserts. If they don’t, it’s `NULL`.

Good practice:

```sql
INSERT INTO events (ts, user_id, action, request_id) VALUES (..., ..., ..., generateUUIDv4());
```

### 4) Update Readers

Be tolerant:

```sql
SELECT
  ts,
  user_id,
  action,
  request_id
FROM events
WHERE (request_id IS NULL AND ts < now() - INTERVAL 7 DAY) -- transitional logic
   OR (request_id IS NOT NULL AND ts >= now() - INTERVAL 7 DAY);
```

Or for joins/analytics:

```sql
SELECT
  coalesce(request_id, toUUID('00000000-0000-0000-0000-000000000000')) AS rid,
  count()
FROM events
GROUP BY rid;
```

### 5) Optional: Backfill Recent Partitions

If analytics benefits from full coverage for, say, this quarter:

```sql
ALTER TABLE events
  UPDATE request_id = cityHash64(toString(user_id))::UUID  -- example derivation
  WHERE ts >= toDate('2025-07-01') AND request_id IS NULL;
```

Watch progress:

```sql
SELECT * FROM system.mutations WHERE table = 'events' ORDER BY create_time DESC;
```

### 6) Optional: Add an Index

If you filter a lot by `request_id`:

```sql
ALTER TABLE events
  ADD INDEX idx_req request_id TYPE bloom_filter GRANULARITY 4;

ALTER TABLE events MATERIALIZE INDEX idx_req;
```

This builds the index for historical parts (I/O heavy); new parts build it on insert.

---

## Observability While You Change Things

-   **`system.mutations`**: status, progress, failures.
-   **`system.replication_queue`**: check for stuck replicated ALTERs.
-   **`system.parts`**: track part counts and sizes; big spikes during materialization are normal.
-   **`system.query_log`**: compare CPU time and read rows for queries that touch the new column.
-   **Disk/IO metrics**: backfills and index materialization are bandwidth-hungry.

---

## Rolling Back

Need to undo? Two paths:

-   **Stop using it**: simplest operationally; leave the column in place, update queries to ignore it. Zero risk.

-   **Drop it**:

    ```sql
    ALTER TABLE events DROP COLUMN request_id;
    ```

    Metadata-only and fast. If you materialized data for it, dropping removes the files in newly written parts as mutations/merges progress. Existing queries that referenced it will fail—be coordinated.

---

## Edge Cases & Advanced Notes

-   **Adding to a `ReplacingMergeTree` with a `version` column:**
    Backfills can create multiple versions of rows with/without the column populated. That’s fine; the engine’s rules still pick the newest by `version` or `sign`. Be mindful of the mutation order.

-   **TTL Expressions:**
    If you add a column used by a `TTL` clause later, you’ll trigger rewrites as TTLs fire on parts. Plan TTL materialization and disk layout (`MOVE TO VOLUME`/`DISK`) after the column stabilizes.

-   **Constraints & Defaults Order:**
    If your default references another column, ensure that column already exists and has a value at the time of evaluation. Generally safe when adding, but can surprise you if you interleave multiple ALTERs quickly. One ALTER per deployment step is kinder.

-   **Version Skew:**
    Clusters running mixed ClickHouse versions may handle “materialize on merge” behavior slightly differently. If you rely on merges to backfill, validate in staging that merged parts indeed contain the column.

---

## A Deployment Checklist

Print this and stick it to your on-call wall:

1. **Plan**

    - [ ] Decide on type (`Nullable`?), codec, and default (constant if possible).
    - [ ] Inventory MVs, projections, and downstream jobs.
    - [ ] Check disk headroom if you will materialize or create indices.

2. **Stage**

    - [ ] Apply on staging with representative data volume.
    - [ ] Run queries that will use the new column; measure query CPU.

3. **Alter**

    - [ ] `ALTER TABLE ... ADD COLUMN ... [ON CLUSTER ...]`
    - [ ] For `Distributed`, ensure all shards have the change.

4. **App Rollout**

    - [ ] Update readers first to tolerate absence/NULLs.
    - [ ] Update writers to populate the new column.

5. **(Optional) Backfill**

    - [ ] Decide scope (which partitions).
    - [ ] Run `ALTER TABLE ... UPDATE ... WHERE ...` or `MATERIALIZE COLUMN`.
    - [ ] Monitor `system.mutations`, disk, and query impact.

6. **(Optional) Optimize**

    - [ ] Add indices/projections and materialize.
    - [ ] Consider `MODIFY COLUMN` to non-nullable once stable.

7. **Validate**

    - [ ] Compare query performance and correctness.
    - [ ] Confirm schema parity across shards/replicas.

---

## Frequently Asked “Wait, But Does It…”

**…lock the table?**
No full lock. `ADD COLUMN` is metadata-only and online. Inserts/queries continue.

**…rewrite data immediately?**
No. Old parts remain untouched. Reads synthesize values; you can materialize later.

**…affect primary key or sorting key?**
Only if you explicitly **modify** those keys (separate ALTER). Plain `ADD COLUMN` does not.

**…break `SELECT *` clients?**
It can change result shape. Stabilize consumer schemas or avoid `*` for external interfaces.

**…work for non-MergeTree engines?**
Semantics can differ (e.g., `Memory`, `Log` engines). The discussion here focuses on `MergeTree` and descendants (`ReplicatedMergeTree`, `ReplacingMergeTree`, `SummingMergeTree`, etc.), which are most common in production.

---

## Key Takeaways

-   **Adding a column is fast because ClickHouse doesn’t rewrite old parts.** It updates metadata and synthesizes values on read for historical data.
-   **Your main decision is when (or if) to materialize.** Constant defaults? Usually don’t bother. Computed defaults used in hot paths? Materialize when convenient.
-   **Think in terms of compatibility and rollouts.** Prefer `Nullable` for transitional changes, update readers before writers, and test materialized views.
-   **Mind the cluster.** Use `ON CLUSTER`, verify schema parity, and watch mutations and merges.
-   **Be intentional about codecs, indices, and projections.** Add them with eyes open to the rewrite costs.

---

## Further Reading & Ideas to Explore

-   ClickHouse official docs on `ALTER TABLE` (ADD/MODIFY/DROP, materialization, and mutations).
-   System tables: `system.parts`, `system.mutations`, `system.query_log`, `system.replication_queue`.
-   Designing rollouts with `Nullable` and sentinel defaults in columnar stores.
-   Performance patterns for data-skipping indexes and `LowCardinality`.
-   Projections for accelerating specific query shapes after schema changes.
