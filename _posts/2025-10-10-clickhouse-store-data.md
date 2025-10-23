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
    overlay_image: /assets/images/clickhouse-store-data/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/clickhouse-store-data/banner.png
title: " Parts, Not Pages: A Mental Model for How ClickHouse Stores Data"
tags:
    - ClickHouse
    - Data Store
---

If you’ve used ClickHouse for more than ten minutes, you’ve probably seen mysterious words in system tables and error messages: **parts**, **granules**, **marks**, **mutations**, **merges**. They sound like spare bolts left over after assembling a bike. But these are the core pieces of ClickHouse’s storage engine—and if you reshape your mental model around them, a lot of ClickHouse’s behavior (and performance) suddenly makes sense.

This post is a guided tour of how ClickHouse stores data. We’ll build a mental model centered on **parts**, *not* pages. We’ll contrast that with page-oriented systems, then progressively peel back how inserts become immutable parts on disk; how primary-key ordering, granules, and marks enable blazing-fast scans; how merges and mutations rewrite data; and how replication uses parts as the unit of truth.

The aim is to give you an intuition-rich picture you can carry into query design, schema choices, and ops decisions—without needing to memorize file extensions.

---

## Why “parts,” not “pages”?

Many databases (think InnoDB, SQL Server, Postgres) are **page-based**. Data lives in fixed-size blocks (e.g., 8 KB). Reads and writes move pages around; indexes map logical rows to pages; and background processes vacuum or defragment pages. Your mental model is: *tables are piles of pages*.

ClickHouse is radically different. It’s a **columnar, append-optimized** system. Instead of scribbling into random pages, it writes **immutable chunks** of data to disk, each chunk called a **data part**. Every insert creates one or more parts. Background merges compact parts into bigger parts. Queries read only the columns they need, and they “jump” through parts using lightweight in-memory indexes and on-disk **marks**.

So your mental model becomes: *a table is an ordered forest of parts*. Each part is a mini columnar dataset—self-contained, immutable, and ordered by the table’s primary key.

That shift—from pages you constantly mutate to parts you append and rewrite—explains almost everything that feels unique about ClickHouse: crazy-fast inserts, compression, predictable scans, and simple crash recovery.

---

## A 10,000-foot view: the MergeTree family

Most production ClickHouse tables use an engine in the **MergeTree** family (e.g., `MergeTree`, `ReplacingMergeTree`, `SummingMergeTree`, `AggregatingMergeTree`, `VersionedCollapsingMergeTree`). They all share the same bones:

* **Immutable parts** stored on disk (or object storage).
* Parts are **ordered** by a **primary key** expression you choose.
* A background thread **merges** parts with overlapping key ranges.
* Queries **skip** large swaths using a sparse in-memory primary index and **data-skipping** indices (min/max, bloom filters, etc.).
* **Granules** and **marks** define how data is chunked within a column file for efficient reads.
* Deletes and updates are **mutations**, implemented as “rewrite into new parts.”

Let’s unpack each layer.

---

## From INSERT to part: the write path

When you `INSERT` into a MergeTree table:

1. **Data lands in RAM** in a mutable buffer (a “block”).

2. The block is **sorted by the primary key** (not necessarily unique; ClickHouse doesn’t enforce uniqueness).

3. The block is **flushed** to disk as a **new part**. That part contains:

   * The data columns, each compressed and stored by **granules**.
   * Lightweight metadata (min/max per column, row count, checksums).
   * A sparse **primary key index** (in-memory on read).
   * **Mark files** describing where each granule starts.

4. Once the part is durable, it’s made **visible** to queries. No half-written pages; no WAL replay guessing games. The part is either there or it isn’t.

A part is **immutable**. You’ll never see ClickHouse “update” a part in place. If rows need to change, a **mutation** creates new parts and discards old ones once they’re no longer needed.

> Quick aside: Why immutability? It simplifies crash recovery, concurrency, and replication. You can reason about storage as a set of versioned snapshots instead of a soup of page deltas.

---

## Primary key vs. sorting key: who’s in charge?

ClickHouse has two related ideas:

* **Primary key**: a sparse index stored in memory at query time; used for range pruning.
* **ORDER BY (sorting key)**: the physical order of rows within each part.

In many schemas they’re identical (`ORDER BY (ts, user_id)` and primary key = same expression). You can define a **wider** sorting key than the primary key; the engine will still maintain physical order by the sorting key while the sparse index uses the primary key prefix. The critical point: **ClickHouse relies on order** for fast scans and merges; it’s not about random point lookups via B-trees.

---

## Inside a part: columns, granules, and marks

A data part is a tiny columnar dataset. Imagine a part as a folder with files like:

```
/my_table/202510_1_1_0/
  checksums.txt
  count.txt
  columns.txt
  primary.idx
  data_format_version.txt
  col1.bin
  col1.mrk2
  col2.bin
  col2.mrk2
  ...
```

Two storage layouts exist:

* **Wide** parts: each column lives in its own `.bin` with its own `.mrk2` marks file (great for many columns).
* **Compact** parts: multiple columns share a single physical data stream (reduces file count; good for tiny parts).

The star players are:

* **Granules**: contiguous row ranges within a part. Default size is controlled by `index_granularity` (e.g., ~8K rows per granule). Compression and IO happen at the granule level.
* **Marks (`*.mrk2`)**: a per-column map from granule number → on-disk offset. Marks let ClickHouse jump directly to the N-th granule of a column without scanning everything before it.

Think of marks as *bookmarks* into compressed column files, and granules as *chapters*. When a query needs rows that fall into certain key ranges, ClickHouse figures out which **granules** overlap and then seeks to the corresponding **marks** in only the **columns referenced** by the query.

That last bit is core to column stores: if your query selects `COUNT(*)` or just `user_id`, ClickHouse only touches those columns’ files and their marks.

---

## How reads are fast: pruning + skipping + vectorized IO

Let’s say your table is `ORDER BY (event_date, user_id)`, and you run:

```sql
SELECT user_id, sum(revenue)
FROM events
WHERE event_date BETWEEN '2025-10-01' AND '2025-10-15'
  AND country = 'SG'
GROUP BY user_id;
```

ClickHouse speeds this up in three cascading ways:

1. **Part-level pruning** (coarse): Each part stores min/max of its primary key / sorting key columns. Parts whose `[min_key, max_key]` don’t overlap your `event_date` filter are skipped entirely.

2. **Granule-level pruning via primary index** (sparse, in-memory): The `.idx` file loads into memory as a sparse index of primary key values sampled per granule. The engine binary-searches this structure to find candidate granule ranges. This is *why ordering matters*—ranges on the key turn into fewer granules to read.

3. **Data skipping indices** (optional, per column): You can add secondary “skip” indices like `minmax`, `bloom_filter`, `set`, or `tokenbf_v1` on specific columns. For our `country` filter, a token bloom filter can skip granules that provably don’t contain `'SG'`.

Only after those steps does ClickHouse issue IO to the relevant `.bin` files. It seeks to marks for the selected **granules**, decompresses **only those chunks**, and processes them in a vectorized engine (batches of rows). No page cache magic; it’s deterministic, surgical IO.

---

## Granularity knobs and trade-offs

* **`index_granularity`** (rows per granule): Smaller granules → more marks, more index overhead, but finer pruning and potentially less IO for selective queries. Larger granules → fewer marks, better throughput for wide scans. Many production tables stick near the defaults unless they have extreme selectivity needs.

* **`index_granularity_bytes`**: A “soft” granule size based on uncompressed bytes. Helps keep granules balanced for very wide rows.

* **`min_bytes_for_wide_part` / `min_rows_for_wide_part`**: Control when to switch between compact and wide parts.

Rule of thumb: favor defaults until you profile a real workload; then tune granularity to your dominant access patterns.

---

## Background merges: compaction without tombstone debt

Insert-heavy workloads create many small parts. That’s fine—parts are cheap to create. But many tiny parts increase overhead during query planning and indexing. Enter **merges**.

The MergeTree background task continuously picks **adjacent parts with overlapping key ranges** and merges them into bigger parts:

1. Reads the input parts in key order (this is a sequential scan).
2. Applies engine-specific rules:

   * `ReplacingMergeTree`: keeps the latest version per key based on a `version` column.
   * `SummingMergeTree`: aggregates numeric columns within the same key.
   * Others collapse or aggregate according to their semantics.
3. Writes out a **new part** that supersedes the small ones.
4. Atomically swaps metadata to make the new part visible, then deletes the old parts.

This process is *compaction by rewrite*. There are no page-level in-place modifications, no long-lingering tombstones. Storage stays clean, and reads stay efficient.

You can steer merges with settings like `max_bytes_to_merge_at_max_space_in_pool`, but the default heuristics are usually good. Merges are also where TTLs kick in (e.g., moving old parts to cheaper storage or dropping them).

---

## Mutations: how deletes and updates actually work

Because parts are immutable, **`ALTER TABLE ... DELETE WHERE ...`** or **`UPDATE ...`** cannot edit in place. ClickHouse schedules a **mutation**:

* It **rewrites** the affected parts, producing **new parts** that exclude (delete) or rewrite (update) the matching rows.
* The engine keeps query-time **consistency** by serving a snapshot (remember: parts are immutable).
* When the new parts are ready, metadata flips the switch; old parts are garbage-collected when no longer referenced.

In heavy-delete scenarios, prefer **partition-level** operations (e.g., partition by month and `DROP PARTITION`) because they are metadata-only and instant. For rows scattered across partitions, mutations are your tool—just know you’re paying for a rewrite.

---

## Partitions: big boxes for lifecycle and parallelism

In MergeTree, the **partition key** groups rows into **partitions**, each holding many parts. Common choices:

* Time-based partitions (e.g., by month).
* Hash of a tenant/customer id.
* Compound expressions.

Partitions influence:

* **Parallelism**: operations like merges and mutations happen per partition.
* **Data lifecycle**: TTL moves/drops operate per part, which is scoped by partition.
* **Operational controls**: `DETACH/DROP PARTITION`, `FREEZE PARTITION` (backup snapshot) work at this boundary.

Think of partitions as *big boxes* containing many *parts*. Choose a partitioning that matches retention, archival, and data motion needs.

---

## Replication: parts are the unit of truth

In replicated engines (`ReplicatedMergeTree` and friends), each table instance registers under a shared path in a coordination service (ClickHouse Keeper or ZooKeeper). The cluster agrees on **part names** and **merge/mutation logs**. Replication then is simply:

* **Get the list of parts I should have** (from the log).
* **Pull the parts I’m missing** (copy files or fetch from object storage).
* **Confirm checksums** and mark the part as present.

Because parts are immutable and named deterministically (encode partition, min/max block ids, and merge level), reconciliation is straightforward and robust. No replaying fine-grained page diffs; just ensure the same set of parts exists on each replica.

This is also why **zero-copy replication** and **S3/object storage** backends work well: a part is a directory (or object prefix) that can be referenced safely by multiple replicas once materialized.

---

## Snapshot isolation “for free”

A lovely property falls out of immutability: **queries see a consistent snapshot** without heavyweight locking. When a query begins, it obtains the current list of active parts. Even if merges or mutations finish mid-query, they result in *new* parts; your query continues reading the parts it started with. After it finishes, old parts no longer referenced are cleaned up.

That’s multi-version concurrency control (MVCC) at the part level—simple and effective.

---

## Skipping indexes: when and how to use them

Beyond the primary key, you can attach **secondary data skipping indexes** to specific columns. They build summaries per granule and let ClickHouse avoid IO for granules that cannot satisfy a predicate.

Common types:

* **`minmax`**: min/max per granule (great for range filters on monotonic-ish columns).
* **`set`**: exact small set of values per granule (cap on cardinality).
* **`bloom_filter` / `tokenbf_v1`**: probabilistic membership for “value IN set” or substring/token predicates.

Example:

```sql
CREATE TABLE events
(
    event_date Date,
    user_id    UInt64,
    country    LowCardinality(String),
    revenue    Float64,
    properties String,
    INDEX idx_country country TYPE set(1024) GRANULARITY 1,
    INDEX idx_props   properties TYPE tokenbf_v1(0.01) GRANULARITY 2
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, user_id);
```

* `GRANULARITY` here is **per index**, not to be confused with the table’s `index_granularity`. It controls how frequently the skip index records a summary (e.g., every 1 or 2 granules).

Use skipping indexes when:

* Predicates have decent selectivity.
* The column appears often in filters but isn’t a good fit for the primary key.
* You can tolerate extra CPU to evaluate summaries in exchange for less IO.

Avoid them when:

* Predicates are unselective (“`country != 'US'`”).
* The column has extreme cardinality and randomness.
* Your workload is dominated by full scans/aggregations over most rows.

---

## Compression and encodings: column-by-column

Each column’s `.bin` stream is a sequence of compressed blocks aligned to granules. ClickHouse uses codecs like LZ4, ZSTD, and specialized **column encodings** (e.g., LowCardinality dictionary for strings, integer codecs, etc.). Two key implications:

1. **Only touched columns are decompressed.** A narrow query (few columns) is cheaper regardless of table width.
2. **Compression ratio benefits from sort order.** Ordering by a column clusters equal/nearby values, which improves dictionary and run-length opportunities.

You can control codecs at the column level:

```sql
ALTER TABLE events
MODIFY COLUMN revenue Float64 CODEC(ZSTD(3));
```

But don’t overthink it initially—often the defaults are close to optimal, and sort order plus data shape dominate.

---

## TTLs and storage tiers: moving whole parts

Because parts are the atomic unit, TTL-based lifecycle actions operate on parts:

* **`TTL ... TO VOLUME 'archive'`**: move old parts to cheaper disks/S3 volumes.
* **`TTL ... DELETE`**: drop parts past a retention window.
* **Row-level TTL**: implemented via mutation-like rewrites; still materializes as new parts.

Parts keep storage movement discrete and auditable. You can watch it happen in `system.parts` and `system.part_log`.

---

## Practical debugging tour: what to look at

When ClickHouse feels “slow” or “weird,” these views tell you what the parts are doing:

```sql
-- Active and outdated parts
SELECT partition, name, rows, bytes_on_disk, level, marks, modification_time
FROM system.parts
WHERE table = 'events' AND active
ORDER BY partition, level;

-- Merge/mutation activity
SELECT type, database, table, partition_id, source_part_names, result_part_name, create_time, elapsed
FROM system.part_log
WHERE table = 'events'
ORDER BY create_time DESC;

-- Skipping efficiency (roughly)
EXPLAIN indexes = 1
SELECT ...
```

* High **`level`** indicates heavily merged parts; many small level-0 parts suggest merges are lagging.
* Large counts of **tiny active parts** often mean too-small inserts or overwhelmed background merges.
* `EXPLAIN indexes = 1` shows whether primary/secondary indices are pruning granules.

---

## Designing with parts in mind

A few battle-tested guidelines that fall directly out of the parts mental model:

1. **Choose an `ORDER BY` that matches your most common range filters.** If you filter by `event_time` first and then by `user_id`, order by `(event_time, user_id)`. This maximizes range pruning and compression.

2. **Batch inserts.** Aim for inserts that produce parts at least hundreds of thousands of rows (or a few MBs). Too many tiny parts increase overhead and reduce compression. If you must stream, use `async_insert` buffers or materialized views to coalesce.

3. **Partition for lifecycle, not speed.** Partitions mostly help with data management (TTL, drop, freeze) and parallelism. Don’t over-partition (e.g., per-day if you really need per-month); too many partitions fragment merges and complicate ops.

4. **Use skipping indexes sparingly and purposefully.** Add them where predicates are selective and frequent. Measure with `EXPLAIN` before and after.

5. **Prefer partition drops over row deletes.** When feasible, model retention as “drop the old month partition.” It’s instant and avoids rewrites.

6. **Watch merges and mutations.** If merges can’t keep up, adjust merge settings or increase resources on the background pool. Long-running mutations mean you’re rewriting a lot—consider coarser retention or different schema.

7. **Schema width matters less than you think.** ClickHouse only reads columns it needs. Wide tables are fine if queries are narrow and sorted well.

---

## Comparing to Parquet: granules vs. row groups vs. pages

A quick comparison helps anchor terms:

* **Parquet**: a file is split into **row groups**, then each column has **pages** within a group, with page-level stats and dictionaries.
* **ClickHouse part**: analogous to a single Parquet file for a sorted slice of the table. **Granules** are akin to row groups (conceptually), and **marks** play the role of page/row-group offsets for direct seeking. But ClickHouse’s sparse **primary index** and cross-column min/max per part plus optional skipping indices make **multi-part** pruning across the entire table a first-class feature.

The big difference is lifecycle: Parquet files are usually produced offline via batch jobs; ClickHouse parts are produced online, then **merged** continuously to maintain health and order.

---

## Tiny code tour: creating a table that “feels right”

Let’s wire up a realistic MergeTree table and talk through the choices.

```sql
CREATE TABLE events
(
    event_time  DateTime,
    user_id     UInt64,
    country     LowCardinality(String),
    device      LowCardinality(String),
    revenue     Decimal(12, 2),
    props       String,
    -- Data-skipping helpers for common filters
    INDEX country_idx country TYPE set(2048) GRANULARITY 1,
    INDEX device_bf   device  TYPE bloom_filter(0.01) GRANULARITY 2
)
ENGINE = MergeTree
-- Manage lifecycle by month; keeps mutation scope tractable
PARTITION BY toYYYYMM(event_time)
-- Optimize range pruning and compression
ORDER BY (event_time, user_id)
-- Reasonable defaults; tune later if needed
SETTINGS index_granularity = 8192, index_granularity_bytes = 10485760;
```

* **`ORDER BY (event_time, user_id)`**: matches the most common filter pattern—time-range analytics, then per-user drill-downs.
* **Partition by month**: easy retention (`DROP PARTITION`), efficient merges.
* **LowCardinality for strings**: dictionary encoding improves compression and speed.
* **Two skip indexes**: `country_idx` for equality filters; a bloom filter for device strings that aren’t super low-cardinality.

Ingest in batches of, say, 100–500k rows per insert (or buffer via materialized view). Observe merges with `system.part_log`. If your workload mostly counts over time ranges, you might never need more tuning.

---

## Common pitfalls (and the part-centric fixes)

* **“Why so many small files?!”**
  You’re generating lots of tiny parts. Batch larger inserts or enable buffering, and let merges catch up. Consider `min_bytes_for_wide_part` to reduce file count per part via compact parts for micro-batches.

* **“DELETE is slow.”**
  Large row-level deletes trigger huge rewrites (mutations). Prefer partition drops or model soft deletes (filter out `is_deleted = 1` query-side until a periodic mutation compacts).

* **“High CPU but little IO.”**
  Skipping indices or complex expressions might be over-eager. Check `EXPLAIN` to see pruning efficiency. Sometimes removing a poorly selective bloom filter reduces CPU.

* **“Queries read too much.”**
  Revisit `ORDER BY`. If your filters don’t align with the sort key, ClickHouse has to scan more granules. Also ensure you’re selecting only needed columns.

* **“Replica lags behind.”**
  Replication moves parts. If merges are heavy, replicas may choose different merge plans and need to exchange big parts. Tuning merge bandwidth or using shared/object storage can help.

---

## Section summaries

* **Parts over pages**: ClickHouse stores data as immutable, ordered **parts**. Inserts create parts; merges rewrite them; mutations replace them.
* **Granules and marks**: Within each part, **granules** (row ranges) and **marks** (offsets) enable precise columnar IO.
* **Fast reads**: Prune at the part level, then granule level, then with skip indices. Only the referenced columns are read and decompressed.
* **Merges and mutations**: Background merges compact parts; updates/deletes are **rewrites** into new parts. No page-in-place edits.
* **Replication**: Parts are the unit of replication and consensus, making consistency simple and robust.
* **Design hints**: Align `ORDER BY` with filters, batch inserts, partition for lifecycle, and use skipping indices judiciously.

---

## Key takeaways

If you remember only one thing: **ClickHouse is built around parts, not pages.** Think of your table as a time-ordered forest of immutable mini-datasets. Your job is to choose an order that matches queries, feed the engine with decently sized inserts, and let merges keep the forest tidy. With that mental model, performance “mysteries” start looking like predictable consequences of how parts are created, pruned, and merged.

---

## Further reading and experiments

* Explore `system.parts` and `system.part_log` while running inserts and deletes; watch parts appear, merge, and vanish.
* Use `EXPLAIN indexes = 1` on key queries to see pruning behavior.
* Try changing `index_granularity` on a test table and measuring the IO differences for selective vs. full-scan queries.
* Experiment with `SummingMergeTree` or `ReplacingMergeTree` to see how merge semantics alter the resulting parts.

Happy clicking—and may your marks align with your granules.
