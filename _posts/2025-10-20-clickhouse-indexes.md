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
    overlay_image: /assets/images/clickhouse-indexes/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/clickhouse-indexes/banner.png
title: "ClickHouse: Using Indexes, Projections, and Data Skipping for Speed"
tags:
    - ClickHouse
    - Data Store
---

> **TL;DR**
> ClickHouse doesn’t use B‑trees the way OLTP databases do. Its speed comes from:
>
> 1. a _sparse primary index_ on the `ORDER BY` key to jump to relevant ranges,
> 2. _data skipping indexes_ that let it skip whole chunks of data, and
> 3. _projections_—physically reordered, automatically maintained “shadow layouts” (optionally pre‑aggregated) that the optimizer can route your query to.
>    Use the right mix and your “scan 2 TB, return 10 rows” queries start feeling… indecently fast.

---

## Why a different mental model?

If you’re coming from Postgres or MySQL, “add an index” means “build a structure that points to rows.” ClickHouse stores columns separately and reads them in _granules_ (8,192 rows by default). It keeps a **sparse** primary index—one entry per granule—on the `ORDER BY` key so it can jump directly to candidate ranges and avoid scanning irrelevant blocks. The index is tiny enough to live in memory, which is why simple range predicates on your sorting key are lightning fast.

Two other pieces complete the mental model:

-   **Partitions** split data into directories on disk by a key you choose (often monthly buckets). During reads, ClickHouse prunes partitions first, then parts, then granules—so a good partitioning strategy can chop off huge swaths of data before finer-grained filtering even begins.
-   **Granularity** matters. You can tune table‐level granularity, but the default of 8,192 rows is already set for balanced IO; you rarely need to specify it explicitly.

With that model in place, we can talk about the three big levers you have for speed: **primary indexes**, **data skipping indexes**, and **projections**.

---

## 1) The primary (sparse) index—your first and best filter

The `ORDER BY` clause controls how data is laid out on disk and which sparse index gets built. Reads that _constrain by a prefix of that key_ get dramatic pruning: ClickHouse scans the in‑memory index, identifies which granules _might_ match, and only reads those granules from storage.

A few practical guidelines:

-   **Choose your `ORDER BY` based on your most common _filter_ prefix.** For time‑series, that’s often `(event_date, something_low_cardinality)`.
-   **`PRIMARY KEY` vs `ORDER BY`**: if you specify both, `PRIMARY KEY` must be a prefix of `ORDER BY`. Most tables just set `ORDER BY` and let primary=ordering key.
-   **Verify usage** with `EXPLAIN` (more on that below).

**Example**

```sql
CREATE TABLE events
(
  ts DateTime,
  user_id UInt64,
  region LowCardinality(String),
  event_name LowCardinality(String),
  message String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, user_id);
```

This layout makes “last 24 hours for a user” and “time‑bounded aggregations” extremely cheap.

---

## 2) Data skipping indexes—secondary “don’t bother” hints

Traditional secondary indexes (B‑trees) don’t fit column stores. Instead, ClickHouse provides **data skipping indexes** that store lightweight summaries per _index block_ so the engine can decide to skip reading whole blocks. You define them on MergeTree-family tables with:

```sql
INDEX name expression TYPE type(...) [GRANULARITY N]
```

_Each skip‑index block spans `N` table granules_ (so with default granules, `GRANULARITY 4` covers 32,768 rows). Creating a skip index adds two small files per part that store the summary and offsets.

### Which types exist?

ClickHouse ships five skip‑index types; each excels for specific predicates:

| Type                      | Best for                                                                               |
| ------------------------- | -------------------------------------------------------------------------------------- |
| `minmax`                  | `col BETWEEN …` or `>=`/`<=` on loosely sorted or correlated columns                   |
| `set(N)`                  | `IN (…)` when each block has _few distinct values_                                     |
| `bloom_filter([fp_rate])` | “needle in a haystack” equality/`IN` with controllable false positives (default 0.025) |
| `ngrambf_v1`              | substring search (`LIKE '%...%'`) via n‑grams                                          |
| `tokenbf_v1`              | tokenized text search (e.g., `hasToken(message, 'error')`)                             |

> Important: bloom‑style indexes can’t prove absence; they’re _probabilistic_. ClickHouse won’t use them to optimize negated predicates that expect reliable `FALSE` (e.g., `NOT LIKE`, `!=`).

### Adding and materializing skip indexes

Indexes are applied to _new_ parts as data arrives. If you add an index to an existing table, **materialize** it to backfill:

```sql
ALTER TABLE events
  ADD INDEX ix_event_bf (event_name) TYPE bloom_filter(0.01) GRANULARITY 2,
  ADD INDEX ix_region_minmax (region) TYPE minmax GRANULARITY 1;

-- For existing data:
ALTER TABLE events MATERIALIZE INDEX ix_event_bf;
ALTER TABLE events MATERIALIZE INDEX ix_region_minmax;
```

Manipulating skip indexes (`ADD`, `DROP`, `MATERIALIZE`, `CLEAR`) is supported for MergeTree engines.

### Tuning and verification

-   **GRANULARITY** trades index size/CPU for skipping power. Start with `1`–`3` for bloom family on sparse predicates; go higher for `minmax` on correlated columns.
-   **Correlate with `ORDER BY` when you can.** Skip indexes work best when block‑local values are clustered; otherwise each block looks “random” and nothing can be skipped.
-   **Verify** with:

```sql
EXPLAIN indexes = 1
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0
SELECT count() FROM events
WHERE ts >= now() - INTERVAL 1 DAY
  AND event_name IN ('login', 'purchase');
```

`EXPLAIN` will show index types, conditions, and _how many parts/granules were filtered_, and those two settings avoid caching that can mask the effect in ClickHouse ≥ 25.9.

---

## 3) Projections—query‑optimized “shadow layouts”

**Projections** are physically stored, automatically maintained _alternate layouts_ of a table (and can also pre‑aggregate). Think of them as hidden child tables inside each part, with their own `ORDER BY` and primary index. At query time, ClickHouse can choose a projection that scans less data than the base table—no query rewrite necessary.

You can define **two flavors**:

1. **Full‑data projections**: store real columns reordered for a different access pattern; the engine can read _directly_ from them.
2. **Index‑like projections** with `_part_offset` (ClickHouse 25.5+): store just the projection’s sorting key plus an offset back into the base part; reduces storage overhead while still enabling key‑based pruning.

As of **25.6**, ClickHouse can _combine_ multiple projections’ primary indexes to prune parts when your query filters on several independent columns (it still reads from only one projection or the base table; the others are used for _part‑level_ pruning).

### Example: two index‑style projections for different filters

```sql
ALTER TABLE events
  ADD PROJECTION by_user
  (
    SELECT _part_offset
    ORDER BY user_id
  ),
  ADD PROJECTION by_region
  (
    SELECT _part_offset
    ORDER BY region
  );

-- Optional backfill for historical data
ALTER TABLE events MATERIALIZE PROJECTION by_user;
ALTER TABLE events MATERIALIZE PROJECTION by_region;
```

Querying with both filters:

```sql
EXPLAIN projections = 1, indexes = 1
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0
SELECT * FROM events
WHERE user_id = 107 AND region = 'us_west';
```

The plan will show both projections contributing to **part pruning**, and which single source (base or one projection) the read comes from.

### When are projections a great fit?

-   You frequently filter on a column _not_ in the table’s `ORDER BY`, and you want primary‑index‑like pruning for it—without maintaining a separate table.
-   You need **pre‑aggregations** that match your query’s `GROUP BY` (e.g., daily per‑user counts), so the engine can serve results from smaller, precomputed data.

### Limitations & gotchas

-   Projections **don’t support joins** and **don’t support `WHERE` filters inside the projection definition**. If you need joins or filtered precomputations, use materialized views. Projections also can’t be chained and don’t offer separate TTLs from the base table.
-   For existing data you may need to **materialize** the projection (it’s a mutation and can take time; track it in `system.mutations`).
-   The optimizer chooses projections automatically; you can introspect with `EXPLAIN` and system tables like `system.projections` / `system.projection_parts`.

---

## Putting it together: a practical recipe for a logs/events table

Let’s say your workloads are:

-   Time‑bounded dashboards (last 1h / 24h / 7d)
-   “Show me all events for _this_ user”
-   Occasional region‑wide scans
-   “Find error messages containing a phrase”

### 1) Start with a right‑sized table layout

```sql
CREATE TABLE events
(
  ts DateTime,
  user_id UInt64,
  region LowCardinality(String),
  event_name LowCardinality(String),
  message String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)     -- management & coarse pruning
ORDER BY (ts, user_id);       -- primary fast path for time-bounded + user filters
```

_This alone_ gets you far: time‑bounded queries and `(ts, user_id)` range scans are cheap, thanks to the sparse primary index.

### 2) Add targeted skip indexes

```sql
ALTER TABLE events
  ADD INDEX ix_event_bf (event_name) TYPE bloom_filter(0.01) GRANULARITY 2,
  ADD INDEX ix_region_mm (region)     TYPE minmax        GRANULARITY 1,
  ADD INDEX ix_msg_ng (message)       TYPE ngrambf_v1(3, 10000, 3, 7) GRANULARITY 1;

ALTER TABLE events MATERIALIZE INDEX ix_event_bf;
ALTER TABLE events MATERIALIZE INDEX ix_region_mm;
ALTER TABLE events MATERIALIZE INDEX ix_msg_ng;
```

-   `bloom_filter` speeds `event_name IN (…)` when the matches are rare; tweak the false‑positive rate if you’re over‑ or under‑skipping.
-   `minmax` on `region` helps if values are clustered within parts (often true if inserts come from region‑sharded sources).
-   `ngrambf_v1` helps substring search of free text (e.g., `LIKE '%timeout%'`). For tokenized search, consider `tokenbf_v1` combined with functions like `hasToken`.

**Validate**:

```sql
EXPLAIN indexes = 1
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0
SELECT count() FROM events
WHERE ts >= now() - INTERVAL 15 MINUTE
  AND event_name IN ('purchase');
```

You should see fewer parts and granules after each index.

> If you see little or no pruning, suspect: (1) too‑high local cardinality per block (`set(N)` overflows), (2) poor correlation with the `ORDER BY` (blocks look random), or (3) the predicate is a negation (bloom family can’t help).

### 3) Add index‑style projections to accelerate common non‑primary filters

```sql
ALTER TABLE events
  ADD PROJECTION p_user (SELECT _part_offset ORDER BY user_id),
  ADD PROJECTION p_region (SELECT _part_offset ORDER BY region);

ALTER TABLE events MATERIALIZE PROJECTION p_user;
ALTER TABLE events MATERIALIZE PROJECTION p_region;
```

Now this query benefits from both projections for **part‑level** pruning (but will read from just one source), which is useful when your `ORDER BY` isn’t aligned with either predicate:

```sql
EXPLAIN projections = 1, indexes = 1
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0
SELECT *
FROM events
WHERE region = 'us_west' AND user_id = 107
ORDER BY ts DESC
LIMIT 50;
```

### 4) Consider a pre‑aggregating projection for dashboards

```sql
ALTER TABLE events
  ADD PROJECTION daily_user_counts
  (
    SELECT toDate(ts) AS d, user_id, count() AS c
    GROUP BY d, user_id
    ORDER BY d, user_id
  );

ALTER TABLE events MATERIALIZE PROJECTION daily_user_counts;
```

Queries that _match_ the grouping (`GROUP BY d, user_id`) can be satisfied from the smaller aggregated data, cutting CPU and IO dramatically. For more complex aggregations—especially with joins or filters—prefer materialized views instead of projections.

---

## Observability toolbox (so you know it’s working)

-   **`EXPLAIN`**

    -   `EXPLAIN indexes = 1` shows which indexes participated and exactly how many parts/granules/ranges they filtered.
    -   `EXPLAIN projections = 1` lists analyzed projections, whether they were used for part‑level pruning or reading, and what they filtered.
    -   Use `SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0` to get clear, comparable output in v25.9+.

-   **System tables**

    -   `system.projections` — defined projections and their sorting keys.
    -   `system.projection_parts` — per‑projection parts, sizes, and health flags.

---

## Design heuristics and pitfalls

**Start with `ORDER BY`.** The primary index is the heavyweight champion. If your hot queries don’t start by filtering on a prefix of the sorting key, you’re leaving 90% of ClickHouse’s free speed on the table.

**Use skip indexes narrowly.** They’re fantastic when they can **drop entire blocks**, not when every block has a high local cardinality or the predicate is a negation. Err on the side of fewer, well‑placed indexes; they add CPU at read time and space at write time.

**Prefer projections for “alternate orderings,”** not as a panacea. Projections shine when you can say “this column is often filtered, so give it a primary‑index‑like layout too,” or “this aggregation is the same every time.” Keep in mind the limitations (no joins/filters inside the projection, no chaining, shared TTL), and that only one projection is read per query (others may prune parts).

**Materialize when you retrofit.** Adding skip indexes or projections to existing data requires `MATERIALIZE …`; track progress via `system.mutations`. Don’t be surprised if backfilling large historical partitions takes time—it’s a mutation.

**Verify, don’t guess.** Bake `EXPLAIN` into your tuning workflow; it shows concrete “before/after” on parts, marks, and granules. Use `EXPLAIN ESTIMATE` for quick cardinality sanity checks.

---

## Worked micro‑examples

### A. `minmax` rescue for a loosely‑sorted column

```sql
ALTER TABLE events ADD INDEX ix_region_mm (region) TYPE minmax GRANULARITY 1;
ALTER TABLE events MATERIALIZE INDEX ix_region_mm;

EXPLAIN indexes = 1
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0
SELECT count() FROM events
WHERE ts >= now() - INTERVAL 1 DAY AND region = 'europe';
```

If inserts tend to come batched per region (common in sharded producers), `minmax` prunes many granules cheaply.

### B. Bloom filter for needle‑in‑haystack

```sql
ALTER TABLE events ADD INDEX ix_event_bf (event_name) TYPE bloom_filter(0.01) GRANULARITY 2;
ALTER TABLE events MATERIALIZE INDEX ix_event_bf;

EXPLAIN indexes = 1
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0
SELECT * FROM events
WHERE event_name IN ('purchase', 'refund') AND ts >= now() - INTERVAL 1 DAY;
```

A tight `IN` on sparse values should show significant granule filtering. (Remember: not useful for negated conditions).

### C. N‑gram text search

```sql
ALTER TABLE events ADD INDEX ix_msg_ng (message) TYPE ngrambf_v1(3, 10000, 3, 7) GRANULARITY 1;
ALTER TABLE events MATERIALIZE INDEX ix_msg_ng;

SELECT count() FROM events WHERE message LIKE '%timeout%';
```

The n‑gram filter will help prune blocks before evaluating the expensive substring condition.

### D. Multi‑filter with projections

```sql
ALTER TABLE events
  ADD PROJECTION by_user   (SELECT _part_offset ORDER BY user_id),
  ADD PROJECTION by_region (SELECT _part_offset ORDER BY region);

EXPLAIN projections = 1, indexes = 1
SETTINGS use_query_condition_cache = 0, use_skip_indexes_on_data_read = 0
SELECT * FROM events WHERE user_id = 107 AND region = 'us_west';
```

Look for both projections being _analyzed_ for part‑level pruning, with one source selected for the actual read.

---

## Summary

-   **Primary index (sparse)**—built from your `ORDER BY`—is the workhorse. Align it with your hottest filter prefixes and you’ll win big.
-   **Data skipping indexes**—`minmax`, `set(N)`, `bloom_filter`, `ngrambf_v1`, `tokenbf_v1`—help when the primary key doesn’t; tune `GRANULARITY`, respect their limits (especially for negations), and materialize after adding to existing data.
-   **Projections** give you alternate orderings (and optional pre‑aggregation) without extra tables. With 25.5+ you can store `_part_offset` only; with 25.6+ the optimizer can combine multiple projections for **part‑level** pruning on multi‑column filters.
-   **Always verify** with `EXPLAIN … indexes = 1, projections = 1` and disable caches for clarity when benchmarking.

Use these three levers thoughtfully, and ClickHouse will repay you with astonishing query latencies on truly big data—without turning your schema into a hedgehog of ad‑hoc tables.

---

## Further reading

-   **Primary (sparse) indexes** and granules: official overview and animations.
-   **Data skipping indexes** (concepts & examples).
-   **`EXPLAIN`** for indexes/projections and estimate modes (plus helpful settings).
-   **Projections**—how they work, limitations vs. materialized views, `_part_offset`, and multi‑projection pruning.
-   **Partitions**—coarse pruning and management trade‑offs.

Happy (skip‑)indexing!
