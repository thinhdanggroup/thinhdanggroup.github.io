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
    overlay_image: /assets/images/peerdb-schema-revolution/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/peerdb-schema-revolution/banner.png
title: "How We Handle Schema Evolution in Real‑Time Data Pipelines with PeerDB"
tags:
    - PeerDB
    - Schema Evolution
---

_When your product team renames a column at 2:07 a.m., will your analytics still be green at 2:08? This post is about making sure the answer is “yes.”_

Modern applications evolve quickly, and so do their schemas. New features add columns; experiments add tables; cleanup drops fields that seemed like a good idea in Q1. In batch ETL, these changes are annoying. In **real‑time** systems they’re existential: every consumer from dashboards to ML features depends on a contract that is quietly moving beneath them.

In this article, I’ll share the playbook we use to keep data flowing when schemas change—using [**PeerDB**](https://www.peerdb.io) as the engine that moves data out of PostgreSQL and into warehouses (Snowflake, BigQuery, ClickHouse), object stores, and queues. We’ll start from the “why,” walk through how PeerDB models the world, and then get hands‑on with examples that cover the most common (and most painful) schema‑evolution scenarios.

> **Who this is for:** engineers who build/operate real‑time pipelines; analytics engineers who own downstream models; VPs of Data who get paged during column renames.

---

## The moving target: why schema evolution is hard in real-time

A schema is a _contract_. Producers (your application) promise shape; consumers (your warehouse tables, Kafka topics, ML features) promise to interpret it correctly. In real‑time systems:

-   You have **two worlds**: OLTP (Postgres) and OLAP/Queues (Snowflake/BigQuery/ClickHouse/Kafka).
-   Data isn’t only appended; it’s **inserted, updated, and deleted** continuously.
-   Changes must be **non‑destructive** and **backwards compatible** because you always have live consumers.

This is why the old “drop the table and reload nightly” strategy doesn’t fly here. Instead, we need consistent rules for what happens when a column is added, dropped, renamed, or its type changes—rules that protect downstream systems and let upstream teams keep moving.

---

## PeerDB in 90 seconds (and two SQL statements)

**PeerDB** is a Postgres‑first data‑movement engine. You register **peers** (connections) and create **mirrors** (sync jobs). Mirrors come in two flavors:

-   **CDC (Change Data Capture)** mirrors stream row‑level changes from Postgres by reading the WAL (write‑ahead log) and applying them to the destination. ([PeerDB Docs][1])
-   **Streaming Query / Watermark mirrors** run a SELECT with a watermark column (e.g., `updated_at`) and sync its result to a destination, useful for pre‑transformations and denormalization. ([PeerDB Docs][2])

PeerDB supports Postgres as the source and multiple targets (Snowflake, BigQuery, ClickHouse, S3/GCS, and more) for both CDC and watermark‑based replication. ([PeerDB Docs][3])

Here’s a minimal example that snapshots and then streams CDC from Postgres to (say) Snowflake/BigQuery/ClickHouse:

```sql
-- Connect to PeerDB’s SQL interface (it speaks Postgres wire protocol).
-- psql "host=peerdb.local port=9900 user=peerdb password=peerdb"

-- 1) Register peers
CREATE PEER src FROM POSTGRES WITH (
  host='postgres.internal', port='5432',
  user='replicator', password='secret', database='appdb'
);

CREATE PEER dst FROM SNOWFLAKE WITH (
  account='ACME-XYZ', user='ETL', password='•••',
  warehouse='ETL_WH', database='ANALYTICS', schema='PUBLIC'
);

-- 2) Create a CDC mirror
CREATE MIRROR app_cdc
  FROM src
  TO   dst
  WITH TABLE MAPPING (
    public.users:public.users,
    public.orders:public.orders
  )
  WITH (
    do_initial_copy = true,      -- snapshot first, then stream
    soft_delete = true           -- surface deletes as a flag
  );
```

-   CDC mirrors do a **full initial load**, then stream WAL changes. If PeerDB can’t match a type, it uses a safe fallback (`TEXT`) and keeps going. ([PeerDB Docs][1])
-   With `soft_delete = true`, PeerDB adds a “logically deleted” column to targets (configurable name), instead of physically deleting rows—safer for downstream consumers. ([PeerDB Docs][1])

---

## What PeerDB does automatically when your schema changes

PeerDB’s behavior is intentionally **conservative** and **non‑destructive**. Here’s the policy the CDC engine applies when it detects a schema change on the source (Postgres):

1. **Add column (`ALTER TABLE … ADD COLUMN …`)**
   → **Propagated automatically**. New writes include the new column in the destination. ([PeerDB Docs][4])

2. **Add column with default (`… ADD COLUMN … DEFAULT …`)**
   → **Propagated automatically for new rows**. Existing rows **don’t** magically backfill the default; you’ll need a refresh/resync if you want historical rows to show that default. ([PeerDB Docs][4])

3. **Drop column (`ALTER TABLE … DROP COLUMN …`)**
   → **Detected, but not propagated**. The destination **keeps** the column; values for subsequent rows become **NULL**. This avoids destructive changes and breaking downstream jobs in the middle of a stream. ([PeerDB Docs][4])

Special case: **Partitioned tables** (very common in high‑scale Postgres) are handled natively. New partitions get replicated automatically; adding a column to the parent is supported; dropping a partition **doesn’t delete** past data in the warehouse (by design—analytics teams rarely want automatic hard deletes). ([PeerDB Docs][5])

---

## Why we chose these behaviors

Real‑time is about **availability** first. Automatically back‑filling defaults or dropping target columns sounds nice until you realize it can:

-   Lock big tables (bad for OLTP),
-   Break downstream jobs mid‑pipeline,
-   Or destroy historical data that other teams expect to remain queryable.

By **propagating additive changes** and **quarantining destructive ones** (turning drops into NULLs), PeerDB keeps the pipe flowing while you decide how to evolve downstream models and dashboards on your own cadence. When you’re ready to materialize the new world, PeerDB provides a **Resync** button that re‑creates target tables with updated schema and atomically swaps them in. ([PeerDB Docs][6])

---

## A gentle internals tour (so the rules make sense)

-   **CDC mirrors** watch Postgres WAL, pull INSERT/UPDATE/DELETE, and apply them to the destination. As a rule, PeerDB tries to map source types to destination types; when there’s no perfect match, it **falls back to `TEXT`** to stay available. ([PeerDB Docs][1])
-   PeerDB maintains a **datatype matrix** (NUMERIC precision rules; JSON/JSONB conversion details; how geospatial gets represented; how BigQuery arrays can’t contain `NULL`, so they’re sanitized, etc.). These are boring but critical details that make long‑running mirrors… actually long‑running. ([PeerDB Docs][7])
-   For streaming‑query mirrors, PeerDB ships data in **Avro** and uses **parallelism** during read/write for throughput; it’s designed to pre‑transform on the source (joins, casts, aliases) and keep targets simple. ([PeerDB Docs][2])

---

## The “expand‑contract” playbook (with PeerDB commands)

The safest way to evolve schemas in real‑time is to **expand** first (add new shape), **migrate** consumers, and **contract** later (clean up). Below are canonical scenarios and how we handle each.

### 1) Add a column

Good news: this is easy. Just add it in Postgres; PeerDB picks it up and writes it to the target.

```sql
ALTER TABLE public.users ADD COLUMN marketing_opt_in boolean;
-- New rows stream with the new column. Old rows remain without it.
```

If you want historical rows to show a default:

-   Backfill in Postgres (generates WAL → replicated), or
-   Do a **Resync** to rebuild target tables atomically with a full copy, then re‑enter CDC. ([PeerDB Docs][6])

### 2) Add a column with `DEFAULT`

Also easy. PeerDB propagates it for **new** rows. If you want historical rows to show the default, run a backfill or resync as above. ([PeerDB Docs][4])

### 3) Drop a column

PeerDB will **not** drop it on the destination; it sets NULL for new rows. This keeps dashboards and dbt models from exploding mid‑flight.

When you’re ready to really remove it:

-   Update downstream code to stop reading it,
-   Optionally **Resync** so the dropped column disappears from the target (the resync workflow creates `_resync` tables, snapshots, swaps them in, and continues CDC). ([PeerDB Docs][6])

### 4) Rename a column

A rename is equivalent to “add new column, backfill, then drop old.” Two options:

**A. Do it at the source and resync later**

```sql
ALTER TABLE public.users ADD COLUMN full_name text;
UPDATE public.users SET full_name = first_name || ' ' || last_name;

-- Dual-write in application for a period:
--   old field (first_name/last_name) + new field (full_name)

-- When downstream is ready, drop old columns at source, then Resync.
```

**B. Keep the source stable and transform in PeerDB**

Use a **Streaming Query** mirror that aliases columns to the _new_ names on the destination:

```sql
CREATE MIRROR users_transform
  FROM src TO dst FOR
$$
  SELECT
    id,
    first_name || ' ' || last_name AS full_name,
    created_at,
    updated_at
  FROM public.users
  WHERE updated_at BETWEEN {{.start}} AND {{.end}}
$$
WITH (
  destination_table_name = 'public.users_v2',
  watermark_table_name   = 'public.users',
  watermark_column       = 'updated_at',
  mode                   = 'upsert',
  unique_key_columns     = 'id',
  refresh_interval       = 30
);
```

Now downstream reads from `users_v2`; once everyone migrates, you can retire the old target. (This is also a nice way to keep OLTP tables lean: let PeerDB denormalize and rename on the way out.) ([PeerDB Docs][8])

### 5) Widen a type (e.g., `INT` → `BIGINT`, `NUMERIC(10,2)` → `NUMERIC(38,20)`)

Do the widen at source; PeerDB will map to an appropriate destination type. Edge cases exist (every warehouse has opinions): consult the type matrix and, if necessary, do a **cast** in a streaming‑query mirror to normalize precisely. ([PeerDB Docs][7])

```sql
-- Cast while transforming:
SELECT id::bigint AS id, amount::numeric(38,20) AS amount FROM payments ...
```

### 6) Narrow a type (e.g., `TEXT` → `INT`)

Don’t narrow in place unless you’ve cleaned the data. Safer: create a new column, populate with validated/cast values, migrate consumers, then drop the old column and resync. If you must enforce the narrow type in the warehouse only, use a transforming mirror and `SAFE_CAST`/`TRY_TO_NUMBER` semantics as appropriate for the destination.

### 7) Generated columns and computed keys

Postgres **generated columns** aren’t published by `pgoutput` logical replication. If a generated column participates in your primary key, deduplication gets messy downstream. The fix: **recreate generated columns at the destination** (dbt or warehouse SQL) and **avoid using them as primary keys** in replicated tables. ([PeerDB Docs][9])

---

## Excluding PII (and other practical guardrails)

It’s common to exclude PII or bulky blobs (e.g., `bytea`) from analytics replicas. PeerDB supports **column exclusion** directly in table mappings:

```sql
CREATE MIRROR app_cdc_snowflake
  FROM src TO dst
  WITH TABLE MAPPING (
    { from: public.users,  to: public.users,  exclude: [email, phone] },
    { from: public.orders, to: public.orders, exclude: [payment_token] }
  )
  WITH ( do_initial_copy = true );
```

That JSON‑like table‑mapping form is handy when exclusions differ per table. (There’s also an API surface where you can provide `exclude` lists, and a UI for editing mirrors if you prefer clicking to typing.) ([PeerDB Docs][10])

If you do need deletes to show up but want downstream safety, remember you can configure **soft deletes** and optional column names for “synced_at” and “is_deleted” markers:

```sql
WITH (
  soft_delete = true,
  soft_delete_col_name = '_is_deleted',
  synced_at_col_name   = '_synced_at'
)
```

This preserves history while letting downstream filters exclude logically deleted rows. ([PeerDB Docs][11])

---

## Type‑system realities: what actually lands in the warehouse

Every destination has quirks. A few we plan for:

-   If a type doesn’t have a perfect equivalent, PeerDB **falls back to `TEXT`** rather than failing the pipeline. You can then cast in warehouse SQL later. ([PeerDB Docs][1])
-   **NUMERIC/DECIMAL** are mapped with destination‑specific precision/scale rules (e.g., Snowflake `NUMBER(38,20)`, BigQuery `BIGNUMERIC(38,20)`, ClickHouse `Decimal(76,38)`). ([PeerDB Docs][7])
-   Big JSON numbers that aren’t IEEE‑754 friendly get stringified to avoid corruption; BigQuery **arrays can’t contain `NULL`**, so those are pruned. ([PeerDB Docs][7])
-   Geospatial values are normalized (e.g., WKT text for warehouses) and invalid shapes are written as `NULL` with logs retained. ([PeerDB Docs][7])

The net effect: your mirrors **keep running**, and you keep the option to tighten types downstream when ready.

---

## Operational muscle: monitor, resync, and heartbeat

**Monitoring:** PeerDB exposes native metrics in tables under the `peerdb_stats` schema. These cover batch sizes, LSN positions, partition progress for streaming‑query mirrors, and replication slot size. You can query them like any other Postgres table:

```sql
-- How far behind are we on CDC?
SELECT mirror_name, source_lsn, destination_lsn
FROM peerdb_stats.cdc_flows
ORDER BY mirror_name;

-- How big are our query partitions?
SELECT mirror_name, partition_id, rows, retries
FROM peerdb_stats.qrep_partitions
ORDER BY started_at DESC;
```

This gives you visibility to _prove_ that “it’s not stuck.” ([PeerDB Docs][12])

**Resync:** When you need to adopt a major schema change (or change ClickHouse ORDER BY keys, or recover from an invalid slot), use **Resync**. Under the hood PeerDB drops the old mirror, creates `_resync` tables, performs a fresh snapshot, then atomically swaps them in and resumes CDC—no manual dance with temp tables. ([PeerDB Docs][6])

**Heartbeat:** To keep the logical replication slot healthy during low‑write periods, include a tiny “heartbeat” table in your CDC mirror and update it periodically; this ensures steady slot consumption and prevents WAL bloat. ([PeerDB Docs][13])

---

## Putting it together: an end‑to‑end recipe

Let’s wire a small but production‑ready pipeline that’s resilient to schema evolution:

```sql
-- 1) Peers
CREATE PEER src FROM POSTGRES  WITH (...);
CREATE PEER wh  FROM BIGQUERY  WITH (...);

-- 2) CDC mirror with exclusions, soft deletes, and audit columns
CREATE MIRROR app_cdc
  FROM src TO wh
  WITH TABLE MAPPING (
    { from: public.users,  to: public.users,  exclude: [email, phone] },
    { from: public.orders, to: public.orders, exclude: [payment_token] },
    public.heartbeat:public.heartbeat
  )
  WITH (
    do_initial_copy           = true,
    soft_delete               = true,
    soft_delete_col_name      = '_deleted',
    synced_at_col_name        = '_synced_at',
    snapshot_num_tables_in_parallel = 4
  );

-- 3) A streaming-query mirror that pre-transforms for an analytics‑friendly table
CREATE MIRROR users_v2
  FROM src TO wh FOR
$$
  SELECT
    id,
    first_name || ' ' || last_name AS full_name,
    DATE_TRUNC('day', created_at)  AS created_day,
    updated_at
  FROM public.users
  WHERE updated_at BETWEEN {{.start}} AND {{.end}}
$$
WITH (
  destination_table_name = 'public.users_v2',
  watermark_table_name   = 'public.users',
  watermark_column       = 'updated_at',
  mode                   = 'upsert',
  unique_key_columns     = 'id',
  refresh_interval       = 5
);
```

What you get:

-   A CDC mirror that **keeps running** across additive/dropping changes using the rules above; destructive changes are quarantined.
-   A transformed mirror to **rename** and **denormalize** without touching the OLTP schema yet.
-   The ability to **resync** when you are ready to make the new schema “official.” ([PeerDB Docs][4])

---

## Design note: why non‑destructive beats “magical auto‑sync”

Some tools attempt to mirror every DDL verbatim, which feels neat but tends to explode when down‑stream systems are slow, schemas diverge, or teams iterate asynchronously. PeerDB’s approach—**propagate adds, detect drops, require intent for destructive changes**—optimizes for uptime and data safety. When you need to adopt bigger changes, do it via **transforming mirrors** or **resync**, both of which are designed for **atomic** cutovers that don’t surprise your consumers. ([PeerDB Docs][2])

> Historical footnote: in July 2024 PeerDB was acquired by ClickHouse and is being integrated into ClickPipes for native Postgres CDC. If you’re already on ClickHouse Cloud, you can use the Postgres connector powered by PeerDB; otherwise, the standalone PeerDB workflow above works the same. ([ClickHouse][14])

---

## Common gotchas (and how we avoid them)

-   **“My BigQuery array has NULLs.”** BigQuery doesn’t allow nulls in arrays; PeerDB strips them. If your logic relies on explicit nulls, model them as sentinel values or separate columns. ([PeerDB Docs][7])
-   **“Why did this numeric stringify?”** Super‑wide JSON numerics aren’t IEEE‑754‑safe; PeerDB converts them to strings to avoid silent precision loss. Cast them back in warehouse SQL if needed. ([PeerDB Docs][7])
-   **“Clicks broke after I dropped a partition.”** That’s expected: dropping partitions on the source **doesn’t** delete warehouse data automatically. Use downstream retention policies or a transform mirror if you want the warehouse to match partition expiry. ([PeerDB Docs][5])
-   **“Generated column in my PK caused dupes.”** Don’t do that. Recreate generated columns in the warehouse and keep them out of primary keys in replicated tables. ([PeerDB Docs][9])

---

## Summary

-   **Default stance:** be _additive by default_, _conservative on destructive changes_, and _explicit on cutovers_.
-   **PeerDB CDC** mirrors: additive changes just work; drops are quarantined (NULLs); use **Resync** for atomic adoption of major schema changes. ([PeerDB Docs][4])
-   **Streaming‑query mirrors** are your scalpel: rename columns, cast types, denormalize—without touching OLTP. ([PeerDB Docs][8])
-   **Type mapping** has sharp edges; PeerDB favors availability with safe fallbacks and destination‑specific rules. ([PeerDB Docs][1])
-   **Operate like a pro:** monitor `peerdb_stats`, keep WAL healthy with a heartbeat, and prefer expand‑contract over “flip it live.” ([PeerDB Docs][12])

The goal isn’t to eliminate schema evolution—it’s to **make it boring**.

---

## Further reading & docs

-   **Schema change handling:** add/drop/default behaviors. ([PeerDB Docs][4])
-   **CDC setup & WAL basics:** Postgres → BigQuery walkthrough (applies similarly to other targets). ([PeerDB Docs][1])
-   **Partitioned tables support:** add columns, new partitions, and retention behavior. ([PeerDB Docs][5])
-   **Streaming Query Replication:** `CREATE MIRROR … FOR SELECT` pattern and options. ([PeerDB Docs][2])
-   **Datatype matrix:** numeric/JSON/geo and array rules. ([PeerDB Docs][7])
-   **Resync workflow:** atomic rebuild & swap. ([PeerDB Docs][6])
-   **Native metrics:** `peerdb_stats` tables. ([PeerDB Docs][12])
-   **Soft delete & audit columns (API):** naming options for `_deleted`/`_synced_at`. ([PeerDB Docs][11])
-   **ClickHouse + PeerDB (context):** acquisition & integration into ClickPipes. ([ClickHouse][14])

If you want, I can adapt this playbook to your stack (destinations, SLAs, and how aggressively you want to adopt schema changes) and produce ready‑to‑run SQL for your mirrors and resync procedures.

[1]: https://docs.peerdb.io/mirror/cdc-pg-bq "CDC Setup from Postgres to Bigquery - PeerDB Docs: Setup your ETL in minutes with SQL."
[2]: https://docs.peerdb.io/usecases/Streaming%20Query%20Replication/overview "Overview - PeerDB Docs: Setup your ETL in minutes with SQL."
[3]: https://docs.peerdb.io/sql/commands/supported-connectors "Supported connectors - PeerDB Docs: Setup your ETL in minutes with SQL."
[4]: https://docs.peerdb.io/features/schema-changes "Schema Changes Propagation Support - PeerDB Docs: Setup your ETL in minutes with SQL."
[5]: https://docs.peerdb.io/features/replicating-partitioned-tables "Replicating partitioned tables - PeerDB Docs: Setup your ETL in minutes with SQL."
[6]: https://docs.peerdb.io/features/resync-mirror "Resyncing a CDC Mirror - PeerDB Docs: Setup your ETL in minutes with SQL."
[7]: https://docs.peerdb.io/datatypes/datatype-matrix "Datatype matrix - PeerDB Docs: Setup your ETL in minutes with SQL."
[8]: https://docs.peerdb.io/usecases/Streaming%20Query%20Replication/postgres-to-snowflake "PostgreSQL to Snowflake - PeerDB Docs: Setup your ETL in minutes with SQL."
[9]: https://docs.peerdb.io/bestpractices/generated_columns "Generated Columns: Gotchas and Best Practices - PeerDB Docs: Setup your ETL in minutes with SQL."
[10]: https://docs.peerdb.io/sql/commands/create-mirror?utm_source=chatgpt.com "Creating Mirrors - PeerDB Docs: Setup your ETL in minutes with SQL."
[11]: https://docs.peerdb.io/peerdb-api/endpoints/create-mirror?utm_source=chatgpt.com "Create mirror - PeerDB Docs: Setup your ETL in minutes with SQL."
[12]: https://docs.peerdb.io/metrics/native-metrics "Native Metrics - PeerDB Docs: Setup your ETL in minutes with SQL."
[13]: https://docs.peerdb.io/bestpractices/heartbeat?utm_source=chatgpt.com "PeerDB Docs: Setup your ETL in minutes with SQL. - docs.peerdb.io"
[14]: https://clickhouse.com/blog/enhancing-postgres-to-clickhouse-replication-using-peerdb "Enhancing Postgres to ClickHouse replication using PeerDB"
