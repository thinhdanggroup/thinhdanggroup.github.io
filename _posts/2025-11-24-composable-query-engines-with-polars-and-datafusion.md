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
    overlay_image: /assets/images/composable-query-engines-with-polars-and-datafusion/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/composable-query-engines-with-polars-and-datafusion/banner.png
title: "Beyond Postgres and DuckDB: The Rise of Composable Query Engines with Polars and DataFusion"
tags:
    - polars
    - datafusion
    - composable query engine
---

If you’ve been doing data-heavy backend work over the last decade, your mental model probably looks something like this:

-   **Postgres** for OLTP and “small-ish” analytics.
-   **BigQuery / Snowflake / warehouse du jour** for big analytics.
-   **DuckDB** locally when you want the “SQLite of analytics” baked into your app.

That model still works. But there’s a new pattern quietly spreading among Rust and Python engineers:

> Instead of standing up _databases_, they’re embedding _query engines as libraries_ — most often **Polars** and **Apache DataFusion** — and wiring them together into custom, low-latency analytic services.

These systems don’t look like traditional databases. There are no background daemons listening on ports, no catalog servers, no heavyweight migrations. Instead, you import a crate or pip package, hand it an Arrow table, a CSV, or an S3 path, build a lazy query plan, and execute it inline in your process. ([datafusion.apache.org][1])

This post is about that shift: **from “use Postgres/DuckDB” to “compose Polars + DataFusion into your own runtime.”**

---

## 1. From Databases to Query Engines: A Mental Model Shift

Let’s quickly anchor on what Postgres and DuckDB give you.

-   **Postgres**: battle-tested relational database. It owns everything — storage, WAL, concurrency control, planner, executor, catalogs. It’s built for correctness, durability, transactions, and multi-tenant workloads.
-   **DuckDB**: an **in-process** OLAP database. It embeds directly into your app (like SQLite), but focuses purely on analytical queries using a vectorized, columnar execution engine and multi-core parallelism. ([InfoQ][2])

Both are “batteries included.” You give them data and SQL; they handle the rest.

But modern data workloads increasingly look like this:

-   Data lives in **object stores**, message buses, feature stores, parquet lakes.
-   You need **custom ingestion, caching, and access control** logic.
-   You run in **serverless** or short-lived containers.
-   You don’t always want to maintain another “database server” or even a DB file.

What you _really_ want in many of these cases is not “a database” but:

> “A **query engine** I can embed, configure, and combine with my own storage and orchestration.”

That’s the niche where Polars and DataFusion shine:

-   They’re **libraries first**, not products.
-   They’re written in **Rust**, aimed at **multi-threaded, columnar, vectorized** execution. ([Docs.rs][3])
-   They speak **Apache Arrow** as their memory model or interchange format, which makes them composable with each other and with other tools. ([datafusion.apache.org][4])

So instead of handing data over to a database, you now embed the engine _inside_ your service and make it part of your architecture.

---

## 2. What Is a “Composable Query Engine”?

Let’s define it concretely.

A **composable query engine** has a few traits:

1. **Library, not a server**
   You `import datafusion` or `polars` inside your code. There’s no separate process to manage or network protocol to speak. ([datafusion.apache.org][1])

2. **Standard columnar format (Arrow)**
   You can move data in and out as Arrow tables / record batches, often with zero copies. This is the key to mixing and matching engines. ([datafusion.apache.org][4])

3. **Lazy, optimizable query plans**
   Both Polars `LazyFrame` and DataFusion `DataFrame` represent _logical plans_ that are optimized and only executed when you call `collect()`. ([docs.pola.rs][5])

4. **Extensibility via UDFs, custom sources, and catalogs**
   You can add new functions, table providers, or connectors for your domain-specific storage (S3, custom formats, other services). ([Docs.rs][6])

Once you treat the query engine as just another library, it becomes natural to combine it with:

-   Your own object-store abstraction.
-   A bespoke cache or feature store.
-   A FastAPI / Actix / Axum HTTP service.
-   A streaming system (Kafka, Arrow Flight, etc.).

That’s the **composability**: query engine + your infrastructure = a custom “database-shaped” system tailored to your workload.

---

## 3. Polars: The DataFrame Library That Accidentally Became a Query Engine

Most people meet **Polars** as a “fast pandas alternative,” but internally it’s much more interesting: a **multi-threaded query engine** built around a typed, expression-centric API. ([Docs.rs][3])

### 3.1 Eager vs Lazy

Polars has two personalities:

-   **Eager**: feels like pandas. Every operation runs immediately.
-   **Lazy**: you build a **`LazyFrame`** that records your transformations as a logical plan. Execution only happens when you call `collect()`.

From the Rust docs:

> A `LazyFrame` represents a logical execution plan: a sequence of operations to perform on a concrete data source. Operations are not executed until `collect()` is called. ([docs.pola.rs][5])

In Python, a lazy query might look like:

```python
import polars as pl

sales = (
    pl.scan_parquet("s3://my-bucket/sales/*.parquet")     # lazy scan
    .filter(pl.col("timestamp") >= pl.datetime(2025, 1, 1))
    .group_by(
        pl.col("user_id"),
        pl.col("timestamp").dt.truncate("1h").alias("hour"),
    )
    .agg(pl.col("amount").sum().alias("revenue"))
    .sort(["hour", "revenue"], descending=[False, True])
)

# Nothing has executed yet.
top = (
    sales
    .group_by("hour")
    .head(10)            # top 10 users per hour
    .collect(streaming=True)  # now we execute, possibly out-of-core
)
```

Under the hood, Polars performs:

-   **Projection pushdown** (only read needed columns).
-   **Predicate pushdown** (filter at scan level).
-   **Streaming / out-of-core execution** so you can process data larger than RAM. ([GitHub][7])
-   **Multi-threaded execution** with vectorized operators for high CPU efficiency. ([pola.rs][8])

The important bit for composability: **this is all in-process** and driven from your code.

### 3.2 Arrow Interop: Polars as a First-Class Arrow Producer/Consumer

Polars can both **consume** Arrow tables and **export** itself as Arrow, typically zero-copy: ([docs.pola.rs][9])

```python
import pyarrow as pa
import polars as pl

# From Arrow -> Polars
arrow_tbl = pa.table({"x": [1, 2, 3], "y": ["a", "b", "c"]})
df = pl.from_arrow(arrow_tbl)

# From Polars -> Arrow
back_to_arrow = df.to_arrow()
```

That Arrow compatibility is the doorway to composability with **DataFusion** and other Arrow-native systems.

---

## 4. DataFusion: A SQL Engine in Your Library Dependencies

If Polars is “pandas, but secretly a query optimizer,” then **Apache DataFusion** is:

> “A query optimizer and execution engine that happens to expose SQL and DataFrame APIs.”

According to the docs, DataFusion is an **extensible, in-process query engine** using the Arrow memory model, designed for developers building analytic systems in Rust. ([datafusion.apache.org][1])

### 4.1 SessionContext, DataFrames, and Laziness

The main entry point is `SessionContext`:

```rust
use datafusion::prelude::*;

#[tokio::main]
async fn main() -> datafusion::error::Result<()> {
    let ctx = SessionContext::new();

    // Read CSV as a DataFrame (logical plan)
    let df = ctx
        .read_csv("tests/data/example.csv", CsvReadOptions::new())
        .await?;

    // Build up a lazy query
    let df = df
        .filter(col("a").lt_eq(col("b")))?      // WHERE a <= b
        .aggregate(vec![col("a")], vec![min(col("b"))])?  // GROUP BY a
        .limit(0, Some(100))?;                 // LIMIT 100

    // Execute plan and collect results into Arrow RecordBatches
    let results = df.collect().await?;

    Ok(())
}
```

Notice the shape: you chain transformations on `DataFrame` objects (which are _logical plans_), then `collect()` creates and runs the physical plan, returning **Arrow `RecordBatch`es**. ([Docs.rs][10])

You can do the same with SQL:

```rust
use datafusion::prelude::*;

#[tokio::main]
async fn main() -> datafusion::error::Result<()> {
    let ctx = SessionContext::new();
    ctx.register_csv("example", "tests/data/example.csv", CsvReadOptions::new())
        .await?;

    let df = ctx.sql("SELECT a, MIN(b) AS min_b FROM example GROUP BY a").await?;
    let batches = df.collect().await?;

    Ok(())
}
```

DataFusion takes care of parsing, planning, optimizing, and executing the query in a multi-threaded, vectorized engine. ([datafusion.apache.org][1])

### 4.2 Streaming, Custom Sources, and Extension Points

Recent DataFusion releases focus heavily on **streaming and extensibility**: ([flarion.io][11])

-   Many physical operators support an **“Unbounded” execution mode** suitable for infinite streams.
-   You can register **custom table providers** that read from Parquet, CSV, JSON, S3, custom formats, or other services. ([컴퓨터 엔지니어로 살아남기][12])
-   You can plug in **UDFs, UDAFs, and custom planners** for domain-specific logic. ([Docs.rs][6])

DataFusion also has **Python bindings** that mirror the lazy DataFrame API, letting you build and execute plans against Arrow, Parquet, CSV, and in-memory data: ([datafusion.apache.org][13])

```python
from datafusion import SessionContext
from datafusion import functions as F

ctx = SessionContext()

df = (
    ctx.read_parquet("s3://my-bucket/events/*.parquet")
    .filter(F.col("timestamp") >= F.lit("2025-01-01"))
    .group_by("user_id")
    .agg(F.count("*").alias("events"))
)

# Logical plan so far; now execute:
batches = df.collect()  # list[pyarrow.RecordBatch]
```

And, crucially, DataFusion can **import and export Arrow data via the Arrow PyCapsule interface with zero copy**, which makes it easy to glue into other Arrow-compatible projects. ([datafusion.apache.org][14])

---

## 5. Arrow as the “ABI” Between Engines

Here’s where things get fun.

Both Polars and DataFusion:

-   Use **Arrow-like columnar layouts** internally, tuned for cache-friendly, vectorized execution. ([Docs.rs][3])
-   Support **zero-copy import/export** to Arrow tables, record batches, and via the Arrow C Data Interface / PyCapsule. ([docs.pola.rs][15])

That means you can treat **Arrow as the ABI** between engines:

1. Use **DataFusion** to run complex SQL over Parquet in S3.
2. Collect results as Arrow.
3. Hand that Arrow table directly to **Polars** for downstream transformations, feature engineering, or serving to users.

And because it’s all in-process and zero-copy, the overhead of composition is often tiny compared to the query execution itself.

---

## 6. Putting It Together: Polars + DataFusion in a Python Service

Let’s make this concrete with a small example service pattern:

> _Goal_: Build a low-latency “user analytics” service that
>
> -   reads raw events from Parquet in S3,
> -   aggregates them with SQL (DataFusion),
> -   does some windowed feature engineering (Polars),
> -   and returns a JSON payload for your application.

### 6.1 The DataFusion side

```python
# analytics_engine.py
import pyarrow as pa
from datafusion import SessionContext, functions as F

def run_sql_aggregation(s3_path: str) -> pa.Table:
    ctx = SessionContext()

    df = (
        ctx.read_parquet(s3_path)
        .filter(F.col("ts") >= F.lit("2025-01-01"))
        .group_by(
            F.col("user_id"),
            F.date_trunc("hour", F.col("ts")).alias("hour"),
        )
        .agg(F.count("*").alias("events"))
    )

    # Execute -> list[RecordBatch]
    batches = df.collect()
    return pa.Table.from_batches(batches)
```

Here, `df` is lazily built; `collect()` compiles and executes a physical plan over Parquet using a multi-threaded, Arrow-native engine. ([datafusion.apache.org][16])

### 6.2 The Polars side

```python
# features.py
import polars as pl
import pyarrow as pa

def compute_features(table: pa.Table) -> pl.DataFrame:
    # Zero-copy Arrow -> Polars
    df = pl.from_arrow(table)

    return (
        df.sort(["user_id", "hour"])
        .with_columns(
            pl.col("events")
            .rolling_mean(window_size=3)
            .over("user_id")
            .alias("events_rolling_3h")
        )
        .with_columns(
            pl.when(pl.col("events_rolling_3h") > 100)
              .then(True)
              .otherwise(False)
              .alias("high_activity_flag")
        )
    )
```

`pl.from_arrow` and `to_arrow` are designed to operate mostly zero-copy where possible, so you’re not burning time serializing and deserializing between engines. ([docs.pola.rs][9])

### 6.3 A tiny FastAPI/Flask-style endpoint

```python
# service.py
from fastapi import FastAPI
from analytics_engine import run_sql_aggregation
from features import compute_features

app = FastAPI()

@app.get("/users/{user_id}/features")
def user_features(user_id: str):
    # 1) Run SQL aggregation (DataFusion)
    tbl = run_sql_aggregation("s3://my-bucket/events/*.parquet")

    # 2) Feature engineering (Polars)
    df = compute_features(tbl)

    # 3) Filter and return
    row = df.filter(pl.col("user_id") == user_id).to_dicts()
    return {"user_id": user_id, "features": row}
```

You now have:

-   **No database server** to run.
-   Queries that are **multi-threaded, vectorized, and columnar** from end to end. ([pola.rs][8])
-   The ability to **swap out the storage layer** (local FS, S3, HTTP) without touching query logic.
-   A clean seam where you can **unit test** your query and feature logic as normal Python and Rust functions.

This pattern generalizes nicely:

-   Cron job → DataFusion SQL → Arrow → Polars → write features to Redis.
-   gRPC service → DataFusion over Kafka → Polars in-memory → gRPC response.
-   CLI tool → DataFusion SQL over Parquet → Polars → CSV/Parquet/JSON.

---

## 7. “Why Not Just Use DuckDB?”

You might be thinking:

> “But DuckDB _is_ an in-process analytical engine. Doesn’t it already solve this?”

Yes and no.

DuckDB is fabulous — and it even has first-class integration with Polars via Arrow. You can both read Polars frames in DuckDB and return results as Polars DataFrames. ([DuckDB][17])

However, DuckDB still presents itself as a **complete database system**:

-   It owns the catalog, storage, and SQL dialect.
-   It’s dynamic and extensible, but the extension story is focused on SQL extensions, table functions, and plugins.
-   It’s excellent when you want a _single, opinionated engine_.

By contrast, **DataFusion is explicitly positioned as a library** for building your own system — DataFusion itself is used as the core of other distributed engines and servers. ([datafusion.apache.org][1])

Similarly, **Polars is explicitly a DataFrame/query engine** with a rich API, without pretending to manage your storage, transactions, or catalogs. ([pola.rs][8])

That’s the subtle but important distinction:

-   **DuckDB**: “Here’s your analytics database; embed it if you like.”
-   **Polars + DataFusion**: “Here’s a SQL engine and a DataFrame engine. Use them to build _your own_ database-shaped system.”

You can absolutely mix DuckDB into this picture too — it’s Arrow-compatible and plays nicely with Polars — but the architecture mindset is different.

---

## 8. When Does This Pattern Shine?

### 8.1 Good fits

**Composable query engines** excel when:

-   You need **low-latency analytics** tightly coupled to business logic (feature services, dashboards-as-a-service, pricing engines).
-   Your data is **already in lake formats** (Parquet/Delta/IPC) and you don’t want another stateful database.
-   You want **full control** over caching, access control, and resource usage.
-   You’re comfortable thinking in **Arrow, DataFrames, and query plans**.

The combination of:

-   DataFusion’s SQL & DataFrame API over Arrow-friendly sources, ([datafusion.apache.org][13])
-   plus Polars’ extremely fast DataFrame transformations and streaming engine, ([pola.rs][8])

gives you a “lego box” for building serious analytics infrastructure without spinning up yet another warehouse.

### 8.2 Not-so-great fits

There are also cases where you probably _should_ reach for Postgres / a proper DB:

-   You need **ACID transactions** and strong durability guarantees.
-   You’re running **multi-tenant workloads** with complex authorization and isolation requirements.
-   You want **SQL as your primary interface** for many non-engineer users.
-   You’re doing a lot of **small OLTP-style reads/writes**.

Polars and DataFusion live squarely in the **analytical / compute** layer. If you also need a durable system of record, they will usually sit on top of (or beside) a more traditional database.

---

## 9. Internals Tour: How These Engines Actually Work

If you like peeking under the hood, here’s a high-level flow that both Polars and DataFusion follow.

### 9.1 Frontend: parsing / API → logical plan

-   **Polars**

    -   Eager API runs operations immediately.
    -   Lazy API (`LazyFrame`) records operations as a **logical plan DAG**: scans, projections, filters, joins, aggregations. ([docs.pola.rs][5])

-   **DataFusion**

    -   SQL is parsed to an AST, then converted to a logical relational plan (RelNode-like).
    -   DataFrame API directly constructs logical plans. ([Docs.rs][6])

### 9.2 Optimization

Both perform classic and modern query optimizations:

-   Projection and predicate pushdown.
-   Constant folding, expression simplification.
-   Join reordering and statistics-based cost decisions (DataFusion more so). ([컴퓨터 엔지니어로 살아남기][12])

### 9.3 Physical plan & execution

-   The logical plan is turned into an **execution plan**: a tree (or DAG) of **operators**.
-   Operators are **vectorized** and work on Arrow-like columnar batches (e.g., 65K rows at a time), using SIMD and multi-threading. ([Docs.rs][3])
-   Execution often happens in **pipelines**: scan → filter → project → aggregate, with operators pulling/pushing batches.

Both engines are optimized for **single-node, multi-core** performance. DataFusion is also used as the heart of several distributed systems, while Polars focuses on single-machine but can operate on datasets larger than RAM via streaming. ([datafusion.apache.org][1])

---

## 10. Key Takeaways and Further Reading

To recap:

-   **Postgres & DuckDB** are still fantastic — but they’re “complete databases.” Use them when you want someone else to handle catalogs, storage, and SQL semantics.
-   **Polars and DataFusion** represent a newer pattern: **embedded, composable query engines** you wire directly into your service architecture.
-   They speak **Arrow**, which acts as a common ABI, letting you route data between engines with near-zero overhead.
-   You can **combine DataFusion’s SQL + Polars’ expressive DataFrame API** to build highly tailored, low-latency analytical systems without running a separate database process.
-   This approach fits especially well in **lakehouse-style architectures**, custom analytics APIs, and ML feature services.

If you want to keep exploring:

-   **Polars**

    -   Official site & user guide: performance characteristics, lazy API, streaming. ([pola.rs][8])
    -   Out-of-core Polars benchmarks, including comparisons to DataFusion. ([hussainsultan.com][18])

-   **DataFusion**

    -   Official user guide and concepts: architecture, SessionContext, DataFrame, streaming. ([datafusion.apache.org][19])
    -   Blog posts on streaming and recent releases (v4x–5x). ([flarion.io][11])

-   **Ecosystem & interop**

    -   Arrow interop docs for Polars and DataFusion (PyCapsule, C Data Interface). ([docs.pola.rs][15])
    -   DuckDB + Polars integration guide, for a different flavor of composable in-process analytics. ([DuckDB][17])

If you’re already spinning up Postgres for “read-only analytics” or shuttling data in and out of DuckDB for bespoke workloads, it’s worth trying the Polars + DataFusion route. Treat them as _libraries_, not databases — and see what kind of database-shaped systems you can build when the query engine is just another import in your code.

[1]: https://datafusion.apache.org/user-guide/faq.html?utm_source=thinhdanggroup.github.io "Frequently Asked Questions — Apache DataFusion documentation"
[2]: https://www.infoq.com/articles/analytical-data-management-duckdb/?utm_source=thinhdanggroup.github.io "In-Process Analytical Data Management with DuckDB - InfoQ"
[3]: https://docs.rs/polars/latest/polars/?utm_source=thinhdanggroup.github.io "polars - Rust - Docs.rs"
[4]: https://datafusion.apache.org/user-guide/example-usage.html?utm_source=thinhdanggroup.github.io "Example Usage — Apache DataFusion documentation"
[5]: https://docs.pola.rs/api/rust/dev/polars_lazy/index.html?utm_source=thinhdanggroup.github.io "polars_lazy - Rust"
[6]: https://docs.rs/datafusion/latest/datafusion/execution/context/index.html?utm_source=thinhdanggroup.github.io "datafusion::execution::context - Rust - Docs.rs"
[7]: https://github.com/pola-rs/polars?utm_source=thinhdanggroup.github.io "Polars: Extremely fast Query Engine for DataFrames, written in Rust"
[8]: https://pola.rs/?utm_source=thinhdanggroup.github.io "Polars — DataFrames for the new era"
[9]: https://docs.pola.rs/api/python/stable/reference/api/polars.from_arrow.html?utm_source=thinhdanggroup.github.io "polars.from_arrow — Polars documentation"
[10]: https://docs.rs/datafusion/latest/datafusion/execution/context/struct.SessionContext.html?utm_source=thinhdanggroup.github.io "SessionContext in datafusion::execution::context - Rust"
[11]: https://www.flarion.io/blog/streaming-in-modern-query-engines-where-datafusion-shines?utm_source=thinhdanggroup.github.io "Streaming in Modern Query Engines: Where DataFusion Shines"
[12]: https://getchan.github.io/data/paper_review_arrow_datafusion/?utm_source=thinhdanggroup.github.io "Apache Arrow DataFusion 논문 - 컴퓨터 엔지니어로 살아남기"
[13]: https://datafusion.apache.org/python/?utm_source=thinhdanggroup.github.io "DataFusion in Python — Apache Arrow DataFusion documentation"
[14]: https://datafusion.apache.org/python/user-guide/io/arrow.html?utm_source=thinhdanggroup.github.io "Arrow — Apache Arrow DataFusion documentation"
[15]: https://docs.pola.rs/user-guide/misc/arrow/?utm_source=thinhdanggroup.github.io "Arrow producer/consumer - Polars user guide"
[16]: https://datafusion.apache.org/python/user-guide/dataframe/index.html?utm_source=thinhdanggroup.github.io "DataFrames — Apache Arrow DataFusion documentation"
[17]: https://duckdb.org/docs/stable/guides/python/polars?utm_source=thinhdanggroup.github.io "Integration with Polars – DuckDB"
[18]: https://hussainsultan.com/posts/out-of-core-polars/?utm_source=thinhdanggroup.github.io "Hussain Sultan - Out-of-core Polars"
[19]: https://datafusion.apache.org/user-guide/introduction.html?utm_source=thinhdanggroup.github.io "Introduction — Apache DataFusion documentation"
