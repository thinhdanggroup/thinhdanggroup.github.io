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
    overlay_image: /assets/images/tables-distributed-clickhouse-cluster/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/tables-distributed-clickhouse-cluster/banner.png
title: "Creating Tables in a Distributed ClickHouse Cluster: Everything You Really Need to Know"
tags:
    - clickhouse
    - distributed
---

If you’ve just set up a ClickHouse cluster, the next scary step is:
“Okay… now how do I actually create tables the _right_ way so I don’t regret everything in six months?”

This post walks through that step in detail.

We’ll focus on **how to design and create tables in a distributed ClickHouse deployment**: local vs Distributed tables, shards, replicas, `ON CLUSTER`, sharding keys, replication, and the operational gotchas people usually only discover in production.

You don’t need to be a ClickHouse guru—just comfortable with SQL and basic distributed-systems ideas.

---

## 1. Mental model: what “distributed ClickHouse” actually means

Before we touch `CREATE TABLE`, you need a clear mental picture of the main pieces:

-   **Shard** – a subset of the data. Different shards hold _different_ rows.
-   **Replica** – a copy of the data for a given shard. Replicas hold the _same_ rows, for high availability and read scalability.
-   **Local tables** – physical storage tables on each node (usually `MergeTree` or `ReplicatedMergeTree`).
-   **Distributed tables** – logical “router” tables that sit on top of local tables and fan queries/inserts out to shards. They don’t store data themselves. ([ClickHouse][1])
-   **Keeper (ZooKeeper or ClickHouse Keeper)** – coordination service used for replication and distributed DDL (e.g., `ON CLUSTER`). ([ClickHouse][2])

A very common pattern per shard:

```text
[ events_local ]  <-- ReplicatedMergeTree
       ^
       | (replication within shard)
       v
[ events_local ]  <-- ReplicatedMergeTree

then a cluster‑wide logical view:

[ events_dist ]   <-- Distributed over all events_local tables
```

So “creating a table in a distributed ClickHouse deployment” usually means:

1. Define **local tables** (one per shard, per replica).
2. Define **Distributed tables** that point to those local tables.
3. Do it in a way that survives schema changes, node failures, and future growth.

---

## 2. Cluster config & macros: the plumbing your DDL depends on

Table creation in a cluster relies on two key configuration blocks:

1. `<remote_servers>` – describes your cluster topology (shards & replicas). ([ClickHouse][3])
2. `<macros>` – defines variables like `{shard}` and `{replica}` that you use in table definitions. ([ClickHouse][4])

A minimal cluster config might look like this (e.g. `/etc/clickhouse-server/config.d/cluster.xml`):

```xml
<clickhouse>
  <remote_servers>
    <main_cluster>
      <shard>
        <replica>
          <host>ch1</host>
          <port>9000</port>
        </replica>
        <replica>
          <host>ch2</host>
          <port>9000</port>
        </replica>
      </shard>
      <shard>
        <replica>
          <host>ch3</host>
          <port>9000</port>
        </replica>
        <replica>
          <host>ch4</host>
          <port>9000</port>
        </replica>
      </shard>
    </main_cluster>
  </remote_servers>

  <macros>
    <shard>01</shard>    <!-- set differently on each node -->
    <replica>ch1</replica>
  </macros>

  <keeper_server>…</keeper_server> <!-- ZooKeeper or ClickHouse Keeper -->
</clickhouse>
```

Each node has the **same `<remote_servers>`**, but **different `<macros>`** (at least `{shard}` and `{replica}`).

Those macros become building blocks for replicated tables:

```sql
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/events_local',
    '{replica}'
)
```

ClickHouse substitutes `{shard}` and `{replica}` from your config, ensuring:

-   Each shard has its own replication path in Keeper.
-   Each replica knows which zk path to use. ([ClickHouse][4])

You don’t _need_ macros for a trivial setup, but they’re standard practice and save you pain later.

---

## 3. Table engines in a distributed cluster: who does what?

In a distributed deployment you’ll almost always combine:

-   **`MergeTree` / `ReplicatedMergeTree`** – for actual storage.
-   **`Distributed`** – for cluster-wide reads/writes. ([ClickHouse][5])

Quick roles:

### `MergeTree`

-   Non‑replicated.
-   Used for local tables when you don’t need replication (e.g., dev, PoC, or read-only derived tables).

### `ReplicatedMergeTree`

-   Same as `MergeTree` but adds asynchronous replication via Keeper. ([ClickHouse][3])
-   Each replica shares a ZooKeeper/ClickHouse Keeper path; merges & mutations are coordinated.

Typical engine snippet:

```sql
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/events_local',  -- Keeper path
    '{replica}'                                  -- replica ID (macro)
)
PARTITION BY toYYYYMM(event_time)
ORDER BY (user_id, event_time)
```

### `Distributed`

-   Holds no data.
-   Knows:

    -   **cluster name**
    -   **database name**
    -   **local table name**
    -   **optional sharding key expression** for routing inserts. ([devdoc.net][6])

Example:

```sql
ENGINE = Distributed(
    'main_cluster',      -- cluster
    'analytics',         -- remote DB
    'events_local',      -- remote table
    cityHash64(user_id)  -- sharding key expression
)
```

---

## 4. Designing the schema: partitions, ORDER BY, and what matters for distribution

ClickHouse is weird (in a good way) if you’re coming from traditional RDBMSes. When you’re designing tables for a distributed cluster, watch three things:

1. **Primary key / ORDER BY**
2. **Partition key**
3. **Sharding key (for the `Distributed` table)**

### 4.1 ORDER BY (a.k.a. the primary index)

In `MergeTree`-family tables, `ORDER BY` defines the sort key, which is used to build sparse indexes and perform efficient range scans. ([ClickHouse][5])

Good choices:

-   Time-series events:
    `ORDER BY (user_id, event_time)` or `ORDER BY (event_time, user_id)`
-   Metrics:
    `ORDER BY (metric_date, metric_name, dimension_id)`

You want a key that:

-   Matches your most common `WHERE` / `GROUP BY` patterns.
-   Has reasonable cardinality (too low = large ranges to scan).

### 4.2 Partitions

Partitions group data into logical chunks (e.g., by month). They matter for:

-   TTL deletions
-   Efficient `ALTER TABLE … DROP PARTITION`
-   Faster queries when you filter on the partition key ([ClickHouse][7])

Example for a daily partition:

```sql
PARTITION BY toDate(event_time)
```

In a distributed cluster, you want **the same partitioning on every shard**. That way, dropping a partition or moving data behaves consistently everywhere.

### 4.3 Sharding key (for `Distributed` engine)

This is separate from partition key and ORDER BY. The `Distributed` table uses it to decide **which shard** gets each inserted row. ([ClickHouse][8])

Typical options:

-   **User-centric workloads**: `cityHash64(user_id)`
-   **Tenant-based**: `cityHash64(tenant_id)`
-   **Random-ish**: `rand()` or `cityHash64(id)` when access is mostly full-table scans

Guidelines:

-   Pick a key that evenly spreads data across shards.
-   If possible, align it with query access patterns. For example, if most queries filter by `tenant_id`, using `tenant_id` as sharding key means most queries only hit a single shard.

---

## 5. Step-by-step: creating local tables in a distributed cluster

Let’s say you want to store an `events` fact table in database `analytics`.

### 5.1 Create the database on all nodes

In a simple setup:

```sql
CREATE DATABASE IF NOT EXISTS analytics ON CLUSTER main_cluster;
```

`ON CLUSTER` sends this DDL to all the hosts in `main_cluster` via the distributed DDL mechanism (Keeper), so each node gets the same database. ([ClickHouse][9])

### 5.2 Create the local replicated table

Now create a **local table** that will physically store data on each shard/replica:

```sql
CREATE TABLE IF NOT EXISTS analytics.events_local
ON CLUSTER main_cluster
(
    event_time   DateTime,
    user_id      UInt64,
    event_type   LowCardinality(String),
    properties   String
)
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/events_local',  -- Keeper path (with macros)
    '{replica}'                                 -- replica ID macro
)
PARTITION BY toYYYYMM(event_time)
ORDER BY (user_id, event_time)
SETTINGS index_granularity = 8192;
```

Key points:

-   `ON CLUSTER main_cluster` makes sure the same table is created on every node in the cluster definition.
-   The `ReplicatedMergeTree` engine path uses macros so each shard/replica gets the correct Keeper path. ([ClickHouse][4])
-   You can tune partitioning & ORDER BY for your workload.

At this point:

-   Each shard owns unique rows.
-   Each shard has multiple replicas of `events_local`, kept in sync by replication.

---

## 6. Building the Distributed table on top

Now create a cluster-wide logical view that lets you query all shards as if it were a single table:

```sql
CREATE TABLE IF NOT EXISTS analytics.events_dist
ON CLUSTER main_cluster
AS analytics.events_local
ENGINE = Distributed(
    'main_cluster',       -- cluster name from <remote_servers>
    'analytics',          -- remote database
    'events_local',       -- remote table
    cityHash64(user_id)   -- sharding key
);
```

What this does:

-   `AS analytics.events_local` copies the column structure.
-   `Distributed('main_cluster', 'analytics', 'events_local', …)` ties it to all `events_local` tables in that cluster. ([ClickHouse][1])
-   `cityHash64(user_id)` is your sharding function—each node uses it to route inserts.

Now:

-   Reads from `events_dist` fan out to all shards in parallel.
-   Inserts into `events_dist` are routed to a single shard based on the sharding key.

---

## 7. How inserts really work: internal_replication, quorum, and friends

When you insert into a `Distributed` table over replicated local tables, there are a few important settings. The full matrix can get hairy, but here’s the intuition.

### 7.1 `internal_replication`

This setting lives on the `Distributed` table.

-   `internal_replication = 1` (typical)

    -   The `Distributed` table sends data to **one replica per shard**.
    -   That replica writes into `ReplicatedMergeTree`.
    -   Replication then propagates to other replicas.

-   `internal_replication = 0`

    -   The `Distributed` table sends data to **every replica** in a shard.
    -   This is uncommon with `ReplicatedMergeTree`, because you’re doubling network/write load and fighting the replication mechanism.

With `ReplicatedMergeTree`, you almost always want `internal_replication = 1`. ([Stack Overflow][10])

Example:

```sql
ALTER TABLE analytics.events_dist
MODIFY SETTING internal_replication = 1;
```

### 7.2 `insert_distributed_sync` & `insert_quorum` (quick overview)

-   `insert_distributed_sync = 1`

    -   Wait until data is written to remote nodes (via Distributed) before returning.

-   `insert_quorum` (for `ReplicatedMergeTree`)

    -   Ensures a write is replicated to at least N replicas before a commit is considered successful.

The exact interactions are nuanced (and can evolve), but the mental model:

-   `Distributed` settings control **how your query node talks to shard nodes**.
-   `ReplicatedMergeTree` settings control **how replicas within a shard coordinate**.

For many setups, you start with:

```sql
SET insert_distributed_sync = 1;
SET insert_quorum = 2;  -- if you have at least 2 replicas per shard
```

and measure the impact before tuning further. ([Stack Overflow][10])

---

## 8. `ON CLUSTER` and distributed DDL: keeping schemas in sync

Without extra help, `CREATE TABLE` only affects the node you send it to.

In a cluster, that’s a recipe for:

-   Slightly different schemas on different nodes.
-   Queries failing only on specific replicas.
-   3 a.m. debugging sessions.

The **`ON CLUSTER`** clause fixes that:

```sql
CREATE TABLE ... ON CLUSTER main_cluster ...;
ALTER TABLE ... ON CLUSTER main_cluster ...;
DROP TABLE ... ON CLUSTER main_cluster ...;
```

How it works (simplified):

1. Your node writes the DDL into a _distributed DDL log_ in Keeper.
2. Every node with that cluster name picks up the entry and executes it locally.
3. You can monitor progress in `system.distributed_ddl_queue`. ([ClickHouse][9])

Important caveats:

-   All nodes must have the **same `<remote_servers>` cluster definition**.
-   If a node is down, the DDL waits in a queue and is applied when the node comes back (unless you clear it).
-   If you bypass `ON CLUSTER` for schema changes, you can create subtle inconsistencies between replicas.

If you find yourself repeating DDL “just in case” on different nodes, that’s a smell: you should be using `ON CLUSTER`.

---

## 9. Patterns for tables in a distributed ClickHouse deployment

Let’s look at a few common patterns and how table creation fits each.

### 9.1 Sharded fact table + Distributed “front”

We already saw this pattern with `events`:

-   `analytics.events_local`
    `ReplicatedMergeTree`, sharded and replicated.
-   `analytics.events_dist`
    `Distributed` engine, for querying and inserting.

You normally:

-   **Write to `events_dist`** from applications.
-   **Query `events_dist`** for ad-hoc analysis.
-   Possibly **query `events_local`** directly for maintenance or troubleshooting.

### 9.2 Dimension tables: small and often replicated

Dimension tables (e.g., `users`, `accounts`) are often small enough to:

-   Store **fully on each shard** (no sharding), and
-   Still replicate for HA.

You can:

1. Create a **replicated local dimension table**:

    ```sql
    CREATE TABLE IF NOT EXISTS analytics.users_local
    ON CLUSTER main_cluster
    (
        user_id   UInt64,
        name      String,
        country   FixedString(2)
    )
    ENGINE = ReplicatedMergeTree(
        '/clickhouse/tables/{shard}/users_local',
        '{replica}'
    )
    PARTITION BY tuple()
    ORDER BY user_id;
    ```

2. Either:

    - Query `users_local` via a `Distributed` table, or
    - Use table functions like `clusterAllReplicas()` when needed. ([ClickHouse][11])

For many workloads, dimension tables are small enough that the exact sharding scheme is less critical, as long as **every shard has complete data**.

### 9.3 Aggregations via local materialized views

Common pattern:

-   Write raw data into `events_dist`.
-   On each node, a **local materialized view** consumes `events_local` and writes to a per-shard aggregate table.
-   A `Distributed` aggregate table provides cluster-wide view.

Example:

```sql
CREATE TABLE analytics.events_agg_local
ON CLUSTER main_cluster
(
    day       Date,
    event_type LowCardinality(String),
    cnt       UInt64
)
ENGINE = ReplicatedMergeTree(
    '/clickhouse/tables/{shard}/events_agg_local',
    '{replica}'
)
PARTITION BY day
ORDER BY (day, event_type);

CREATE MATERIALIZED VIEW analytics.events_to_agg
ON CLUSTER main_cluster
TO analytics.events_agg_local
AS
SELECT
    toDate(event_time) AS day,
    event_type,
    count() AS cnt
FROM analytics.events_local
GROUP BY day, event_type;

CREATE TABLE analytics.events_agg_dist
ON CLUSTER main_cluster
AS analytics.events_agg_local
ENGINE = Distributed(
    'main_cluster',
    'analytics',
    'events_agg_local',
    cityHash64(event_type)
);
```

This pattern lets you:

-   Distribute aggregation work across shards.
-   Query aggregated data efficiently via `events_agg_dist`.

---

## 10. Operational stuff you’ll wish you knew sooner

### 10.1 Schema changes (ALTER TABLE)

When you alter a table in a distributed setup:

-   **Always** use `ON CLUSTER`, unless you intentionally want divergence.

Example:

```sql
ALTER TABLE analytics.events_local
ON CLUSTER main_cluster
ADD COLUMN device String AFTER event_type;
```

If you forget `ON CLUSTER`:

-   That column might only exist on some nodes.
-   Distributed queries will fail when they hit a replica without the column.

You can also alter the `Distributed` table, but typically the columns and types come from the underlying local table schema.

### 10.2 Adding a new replica

When you add replicas, you usually:

1. Add the node to `<remote_servers>`’ cluster layout.
2. Configure correct `<macros>` for `{shard}` and `{replica}`.
3. Start ClickHouse; create the same **ReplicatedMergeTree** tables using the same Keeper path.
4. The new replica pulls data from existing replicas and catches up. ([Altinity® Knowledge Base for ClickHouse®][12])

As long as:

-   The replication path (e.g. `/clickhouse/tables/01/events_local`) is the same, and
-   The schema matches,

the new replica will “join the party” and backfill data.

### 10.3 Monitoring distributed DDL

Watch:

-   `system.distributed_ddl_queue` – status of cluster-wide DDL. ([ClickHouse][9])
-   `system.replicas` – replication delays & errors.
-   `system.parts` – number/sizes of parts for each table.

These system tables help you spot:

-   Nodes that didn’t apply a DDL.
-   Replicas that are lagging behind.
-   Shards that are accumulating too many parts (bad insert patterns).

---

## 11. A practical checklist: creating a new table in a distributed ClickHouse cluster

When you’re about to introduce a new table, run through this checklist:

1. **Cluster topology confirmed**

    - `<remote_servers>` defines your cluster correctly.
    - `<macros>` set per node (`{shard}`, `{replica}`).
    - Keeper (ZooKeeper or ClickHouse Keeper) is healthy.

2. **Schema design**

    - Columns and types defined.
    - `ORDER BY` matches query patterns.
    - `PARTITION BY` suits your data lifecycle (e.g., daily/monthly partitions).
    - Compression, TTL, and indexes considered if needed.

3. **Local table definition**

    - Use `ReplicatedMergeTree` for anything important.
    - Path uses macros: `'/clickhouse/tables/{shard}/table_name'`.
    - `CREATE TABLE ... ON CLUSTER your_cluster`.

4. **Distributed table definition**

    - `Distributed('cluster', 'db', 'local_table', sharding_key_expr)`.
    - Sharding key spreads data well and aligns with query filters.
    - `internal_replication = 1` if using `ReplicatedMergeTree`.

5. **Application wiring**

    - Writes go to the **Distributed** table, not directly to `_local` tables (unless you know why).
    - Reads usually go to the Distributed table as well.

6. **Schema changes**

    - Always `ALTER TABLE ... ON CLUSTER`.
    - Verify on `system.columns` across nodes if you suspect inconsistency.

7. **Monitoring**

    - Watch replication (`system.replicas`).
    - Watch distributed DDL queue (`system.distributed_ddl_queue`).
    - Track performance and part counts (`system.parts`).

Print this list, stick it near your terminal, and you’ll avoid a bunch of subtle cluster headaches.

---

## 12. Summary and further reading

We covered quite a lot:

-   The building blocks of a distributed ClickHouse cluster: shards, replicas, local and Distributed tables, Keeper.
-   How `MergeTree` / `ReplicatedMergeTree` work with the `Distributed` engine to store and query data across the cluster. ([ClickHouse][5])
-   How to design partitions, ORDER BY and sharding keys for distributed workloads. ([ClickHouse][8])
-   Using `ON CLUSTER` and macros to keep table definitions consistent. ([ClickHouse][9])
-   Practical patterns: sharded fact tables, replicated dimensions, materialized-views-based aggregations.
-   Operational concerns around schema changes, adding replicas, and monitoring.

If you want to go deeper, these are excellent next reads:

-   **ClickHouse Docs – Table Engines (MergeTree family + Distributed)** ([ClickHouse][5])
-   **Replication & Sharding examples in the official deployment guides** ([ClickHouse][2])
-   **Distributed DDL (`ON CLUSTER`) documentation** ([ClickHouse][9])
-   **Altinity & PostHog engineering blogs on ClickHouse sharding and replication** ([PostHog][13])

[1]: https://clickhouse.com/docs/engines/table-engines/special/distributed?utm_source=thinhdanggroup.github.io "Distributed table engine - ClickHouse Docs"
[2]: https://clickhouse.com/docs/architecture/cluster-deployment?utm_source=thinhdanggroup.github.io "Replication + Scaling - ClickHouse Docs"
[3]: https://clickhouse.com/docs/architecture/replication?utm_source=thinhdanggroup.github.io "Replicating data - ClickHouse Docs"
[4]: https://clickhouse.com/docs/engines/table-engines/mergetree-family/replication?utm_source=thinhdanggroup.github.io "Replicated* table engines - ClickHouse Docs"
[5]: https://clickhouse.com/docs/engines/table-engines?utm_source=thinhdanggroup.github.io "Table engines - ClickHouse Docs"
[6]: https://www.devdoc.net/database/ClickhouseDocs_19.4.1.3-docs/operations/table_engines/distributed/?utm_source=thinhdanggroup.github.io "Distributed - ClickHouse Documentation"
[7]: https://clickhouse.com/docs/partitions?utm_source=thinhdanggroup.github.io "Table partitions - ClickHouse Docs"
[8]: https://clickhouse.com/docs/shards?utm_source=thinhdanggroup.github.io "Table shards and replicas - ClickHouse Docs"
[9]: https://clickhouse.com/docs/sql-reference/distributed-ddl?utm_source=thinhdanggroup.github.io "Distributed DDL Queries (ON CLUSTER Clause) - ClickHouse Docs"
[10]: https://stackoverflow.com/questions/63953644/clickhouse-distributed-tables-and-insert-quorum?utm_source=thinhdanggroup.github.io "ClickHouse Distributed tables and insert_quorum - Stack Overflow"
[11]: https://clickhouse.com/docs/sql-reference/table-functions/cluster?utm_source=thinhdanggroup.github.io "clusterAllReplicas | ClickHouse Docs"
[12]: https://kb.altinity.com/altinity-kb-setup-and-maintenance/altinity-kb-data-migration/add_remove_replica/?utm_source=thinhdanggroup.github.io "Add/Remove a new replica to a ClickHouse® cluster"
[13]: https://posthog.com/handbook/engineering/clickhouse/replication?utm_source=thinhdanggroup.github.io "Data replication and distributed queries - Handbook - PostHog"
