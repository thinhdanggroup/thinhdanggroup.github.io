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
    overlay_image: /assets/images/airflow-prefect-dagster/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/airflow-prefect-dagster/banner.png
title: "Comparing Workflow Architectures: Prefect vs. Dagster vs. Airflow"
tags:
    - Prefect
    - Dagster
    - Airflow
---

_What really happens when you “schedule a job”?_ If you’ve ever pushed a button in a nice UI and watched a pipeline spring to life, you’ve probably felt the orchestration black box humming underneath. This post opens that box. We’ll compare **Prefect**, **Dagster**, and **Apache Airflow** from an architectural point of view—how each models work, launches it, watches it, and keeps the whole operation upright when a single task decides to go cliff-diving.

Our goal is to give you a mental model you can actually _use_ when you’re designing systems: which tool’s control plane fits your constraints; how data flows between tasks; and which primitives—DAGs, flows, software-defined assets—will make your pipelines easier (or harder) to evolve.

---

## The Job-to-Be-Done of Orchestrators

All three tools exist to answer the same four questions:

1. **What** should run? (Your units of work and their dependencies.)
2. **Where** should it run? (Worker processes/pods, often on K8s or machines you control.)
3. **When** should it run? (Schedules, sensors/events, or on-demand.)
4. **How** do we know it’s working? (State, retries, logs, lineage, alerts.)

Under the hood, each tool splits responsibilities between **control plane** (scheduling, state, metadata, UI) and **data plane** (your code, your compute). The friction you feel day to day—deployments, backfills, dynamic fan-out, handing off large data—comes from how they draw that line.

We’ll build up a quick mental model for each, then do a side‑by‑side on the decisions that matter.

---

## Airflow: The DAG-Centric Scheduler

**Mental model:** You define a DAG of tasks. A **Scheduler** reads your DAG files, schedules task instances, and hands them to an **Executor** which runs them on **workers**. A **Webserver** provides the UI. Newer versions also include a **Triggerer** for “deferrable” (async) tasks that would otherwise hold a worker while waiting. 

**Why it feels the way it does**

-   **Dependencies are explicit edges** between tasks, with optional data passing via XComs (small payloads or externalized backends). Airflow is opinionated that _data lives outside the scheduler_; XComs are for control-plane sized messages. 
-   **Executors** determine where tasks run (Local, Celery, Kubernetes, and hybrids like CeleryKubernetes). This lets you pick isolation and scalability per deployment. 
-   **Deferrable operators** offload long waits (e.g., external sensors) to the Triggerer so workers aren’t blocked. This reduces fleet size for event-driven DAGs. 
-   **Data-aware scheduling (Datasets)** lets one DAG run when another updates a named Dataset URI—an asset-ish trigger layered onto DAGs. 

**A tiny, idiomatic example (TaskFlow API + dynamic mapping)**

```python
# dags/etl.py
from datetime import datetime
from airflow.decorators import dag, task

@dag(
    start_date=datetime(2024, 1, 1),
    schedule='@daily',
    catchup=False,
    default_args={"retries": 2}
)
def etl():
    @task
    def extract() -> list[str]:
        return ["al", "ak", "az"]  # imagine these came from S3

    @task
    def normalize(code: str) -> str:
        return code.upper()

    @task
    def load(rows: list[str]) -> None:
        print("loading:", rows)

    # Dynamic task mapping: one task instance per element
    normalized = normalize.expand(code=extract())
    load(normalized)

etl()
```

The `expand()` call creates tasks at runtime based on upstream data—great for fan-out workloads. 

**Operational controls you’ll touch**

-   **Pools** throttle concurrency against scarce resources (e.g., “only 5 tasks may hit the warehouse”). **Priority weights** bias scheduling when the queue is full. 
-   **Remote logs** (S3/GCS/etc.) move worker logs out of ephemeral pods so the UI can fetch them later. 

**What this buys you**

Mature DAG-first modeling, a huge integrations ecosystem, and a well-known deployment story from single-node to Kubernetes. If your teams already _think in tasks_, Airflow maps closely to that mental model.

---

## Prefect: Pythonic Flows with a State Machine at the Core

**Mental model:** A **flow** is a Python function that runs your code and tracks state transitions for the flow and its **tasks**. You can run flows _locally_ or as **deployments** that a **worker** picks up from a **work pool**. Prefect’s **control plane** (Prefect Server/Cloud) stores metadata, state, and UI; **workers** submit your code to your compute. 

**Why it feels the way it does**

-   **You write normal Python.** No separate DSL: `@flow` and `@task` wrap functions with retries, timeouts, and state tracking; flows can call flows (“subflows”). 
-   **Task runners** (thread/process pools or distributed runners like Dask) give you parallelism, set by the flow’s `task_runner`. Submit work with `.submit()` or `.map()` and collect results. 
-   **Work pools & workers** connect deployments to execution environments (e.g., Docker, K8s) via a pub/sub-like model. 
-   **Blocks** encapsulate credentials/config/infrastructure; reuse them across deployments. 
-   **Caching & concurrency limits**: per-task caching avoids recompute; tag-based concurrency limits keep hot resources from overload. 
-   **Artifacts** let tasks/flows publish human-friendly tables, markdown, images, and progress bars right into the UI. 

**A tiny, idiomatic example (concurrency + tags)**

```python
# flows/etl.py
from prefect import flow, task
from prefect.task_runners import ThreadPoolTaskRunner

@task(retries=2)
def extract() -> list[str]:
    return ["al", "ak", "az"]

@task
def normalize(code: str) -> str:
    return code.upper()

@task(tags=["warehouse"])  # throttle with a tag-based concurrency limit in the UI
def load(rows: list[str]) -> None:
    print("loading:", rows)

@flow(task_runner=ThreadPoolTaskRunner())
def etl():
    letters = extract()
    # fan-out: tasks run concurrently under the task runner
    futs = [normalize.submit(c) for c in letters]
    load([f.result() for f in futs])

if __name__ == "__main__":
    etl()
```

To productionize, create a **deployment** tied to a **work pool**, then start a **worker** for that pool. The worker polls the pool and launches flow runs on your infra. 

**What this buys you**

Low-friction Python ergonomics (great for embedding orchestration into libraries or notebooks), straightforward local-to-prod lift, and stateful features like caching, artifacts, and tag-based concurrency without a lot of boilerplate.

---

## Dagster: Asset-First Orchestration

**Mental model:** You declare **software-defined assets** (data products) and their dependencies; Dagster maintains an **asset graph** with lineage. A **webserver/UI** shows the catalog; a **daemon** (and run queue) schedules and monitors runs; **run launchers** and **executors** decide where/how user code runs; **I/O managers** define how inputs/outputs are stored/loaded. User code lives in **code locations** (processes) that the system talks to over RPC. 

**Why it feels the way it does**

-   **Assets first.** You model tables/files/models as assets; the tool tracks their materializations, dependencies, partitions, and checks. Jobs and ops exist, but the asset graph is the star. 
-   **I/O managers** put data management front-and-center: they define _how_ artifacts are persisted/loaded (e.g., Parquet in S3), so your compute code stays clean. 
-   **Scheduling options:** classic schedules/sensors and **declarative automation** (auto-materialize based on upstream changes or freshness policies).
-   **Dynamic fan-out** exists via `DynamicOut`/dynamic graphs when you do need runtime-determined parallelism.
-   **Partitions + backfills** are first-class for incremental processing.
-   **Asset checks** (data quality tests) live alongside the assets they validate.

**A tiny, idiomatic example (assets + schedule + simple I/O manager)**

```python
# dagster_project/assets.py
import pandas as pd
import dagster as dg

@dg.asset
def raw_states() -> pd.DataFrame:
    return pd.DataFrame({"code": ["al", "ak", "az"]})

@dg.asset
def normalized_states(raw_states: pd.DataFrame) -> pd.DataFrame:
    df = raw_states.copy()
    df["code"] = df["code"].str.upper()
    return df

class ParquetIOManager(dg.IOManager):
    def handle_output(self, context: dg.OutputContext, obj: pd.DataFrame):
        path = f"/data/{context.asset_key.path[-1]}.parquet"
        obj.to_parquet(path)
    def load_input(self, context: dg.InputContext) -> pd.DataFrame:
        upstream = context.upstream_output.asset_key.path[-1]
        return pd.read_parquet(f"/data/{upstream}.parquet")

@dg.io_manager
def parquet_io_manager():
    return ParquetIOManager()

asset_job = dg.define_asset_job("daily_assets", selection=dg.AssetSelection.all())
daily = dg.ScheduleDefinition(job=asset_job, cron_schedule="0 3 * * *")

defs = dg.Definitions(
    assets=[raw_states, normalized_states],
    resources={"io_manager": parquet_io_manager},
    schedules=[daily],
)
```

Here, the **I/O manager** centralizes persistence (one line per asset in the UI shows lineage and materializations), while a **schedule** periodically materializes the graph. For event-driven automation, you’d attach a declarative condition (e.g., eager auto-materialization) so downstream assets update when upstreams do. 

**What this buys you**

Excellent lineage/observability, data-aware automation, and clean separation of storage concerns. If your team says “asset” more than “task,” Dagster often fits like a glove.

---

## Side-by-Side: Architectural Axes That Matter

### 1) **Unit of composition**

-   **Airflow:** Tasks and DAG edges (with data handoffs via XCom or external stores). Great when your world is external systems stitched by operators. 
-   **Prefect:** Flows & tasks as ordinary Python functions. Subflows are natural; the runtime builds dependency/state as code executes. 
-   **Dagster:** Assets (or ops/jobs) with explicit asset dependencies. The graph itself is a first-class object the UI understands. 

**Takeaway:** Choose the noun that matches your organization’s vocabulary. DAGs → Airflow, flows → Prefect, assets → Dagster.

---

### 2) **Scheduling primitives**

-   **Airflow:** Cron/timetables, **datasets** (data-aware triggers), sensors/deferrable tasks. Catchup/backfill via CLI/UI.
-   **Prefect:** Schedules live on **deployments**; workers poll **work pools**; you can pause/resume, parametrize, and tag runs. 
-   **Dagster:** Classic **schedules**/**sensors**, plus **declarative automation** (auto-materialize based on upstream events/freshness).

**Takeaway:** If you want data change → compute (without hand-rolled sensors), Dagster’s asset automation and Airflow’s datasets are compelling. Prefect leans into ergonomic scheduled deployments.

---

### 3) **Where does user code run?**

-   **Airflow:** The executor dispatches tasks to workers; you pick Celery, Kubernetes, etc., per your scaling/isolation needs. 
-   **Prefect:** A **worker** bridges the control plane and your compute, submitting flow runs to the configured environment; the **task runner** controls intra-flow parallelism.
-   **Dagster:** A **run launcher** creates a run worker; inside it, an **executor** decides process/container/pod execution; **code locations** keep user code isolated and hot-reloadable.

**Takeaway:** All three separate control from compute. Dagster’s code-location model and I/O managers skew toward “platform-y” deployments; Prefect’s workers and task runners make hybrid local/remote execution quite simple.

---

### 4) **Data handling between steps**

-   **Airflow:** XComs are for small control-plane messages; large data should live in external stores; remote logging supported. 
-   **Prefect:** Return Python objects between tasks in-process; for distributed patterns, rely on storage libs or task runners like Dask. Artifacts publish human-friendly results to the UI. 
-   **Dagster:** I/O managers formalize how inputs/outputs are persisted and loaded; the tool treats data materializations as first-class events with metadata. 

**Takeaway:** If you want the orchestrator to _own_ storage patterns and lineage, Dagster shines. If you prefer storage concerns to live in your code/integrations, Airflow or Prefect are a better match.

---

### 5) **Dynamic workflows (fan-out/fan-in)**

-   **Airflow:** Dynamic task mapping (`expand()`) creates tasks at runtime based on upstream data. 
-   **Prefect:** Submit/map tasks against iterables using a task runner for concurrency. 
-   **Dagster:** Dynamic outputs/graphs (`DynamicOut`) expand the graph at runtime; asset-backed patterns exist for fan-out/fan-in.

**Takeaway:** All three support dynamic parallelism. Airflow and Prefect are concise for “map this function over N items”; Dagster is more explicit but integrates with the asset graph.

---

### 6) **Backfills and incremental work**

-   **Airflow:** Backfill/catch-up aligns runs with a schedule timeline; datasets can trigger when producers update.
-   **Prefect:** Re-run flows with parameterized deployments; caching prevents recompute when conditions match. 
-   **Dagster:** Time or key **partitions** and **backfills** are first-class; auto-materialization keeps descendants current.

---

### 7) **Observability & quality**

-   **Airflow:** Web UI per DAG/task, remote task logs; mature operational tooling. 
-   **Prefect:** Rich state machine, retries, artifacts in the UI, tag-based concurrency dashboards. 
-   **Dagster:** Asset catalog with lineage, **asset checks** to codify data contracts in-line.

---

## Code, But Make It Real: Connecting Primitives to Architecture

### Airflow: Dataset-aware cross-DAG trigger

```python
# dags/producer.py
from airflow.datasets import Dataset
from airflow.decorators import dag, task
from datetime import datetime

orders_ds = Dataset("s3://warehouse/raw/orders.parquet")

@dag(start_date=datetime(2024,1,1), schedule='@hourly', catchup=False)
def producer():
    @task(outlets=[orders_ds])
    def write_orders():
        # write to s3://warehouse/raw/orders.parquet
        return "ok"
    write_orders()

producer()
```

```python
# dags/consumer.py
from airflow.datasets import Dataset
from airflow.decorators import dag, task
from datetime import datetime

orders_ds = Dataset("s3://warehouse/raw/orders.parquet")

@dag(start_date=datetime(2024,1,1), schedule=[orders_ds], catchup=False)
def consumer():
    @task
    def load_orders():
        # read from S3 and transform
        pass
    load_orders()

consumer()
```

The **Scheduler** now considers dataset updates as triggers, not just cron, and your **workers** still do the heavy lifting via the configured **executor**. 

---

### Prefect: From notebook to prod, step by step

1. **Develop locally** with a flow & task runner (as shown earlier).
2. **Create a deployment** and attach it to a **work pool**; a **worker** polls and launches the run on your infra.
3. **Add a tag-based concurrency limit** (e.g., `warehouse=5`) so only five `load` tasks run at once across your workspace.

Those three choices map to the control-plane concepts in Prefect: deployments, work pools, workers, and concurrency limits. 

---

### Dagster: Asset-first with storage discipline

In the earlier Dagster sample, notice how the **I/O manager** captures the storage convention (“this asset persists to Parquet at `/data/<asset>.parquet`”). Downstream assets automatically **load** via the same I/O manager, so your asset functions can remain pure transformations. Scheduling with `ScheduleDefinition` or using **declarative automation** keeps the graph fresh without bespoke polling. 

---

## Choosing Under Real Constraints

Here’s a pragmatic cheat sheet based on the axes above:

-   **“We already speak in DAGs and operators.” → Airflow.**

    -   Strongest fit when a central platform team runs the control plane, and many teams contribute DAGs that integrate dozens of external systems. The **executor** palette (Celery/Kubernetes) scales from laptop to cluster, and **datasets** give you a bridge toward data-aware triggers without abandoning DAGs. 

-   **“We want orchestration to disappear into Python.” → Prefect.**

    -   Write flows and tasks like normal code, choose a **task runner** for parallelism, and promote to **deployments** when ready. You get sane defaults for state, retries, caching, and **artifacts** that make results visible to humans. **Work pools/workers** cleanly separate control and compute. 

-   **“Our source of truth is the data graph.” → Dagster.**

    -   If you care deeply about lineage, partitions, and keeping downstream assets up-to-date when upstreams change, Dagster’s **assets**, **I/O managers**, **asset checks**, and **declarative automation** are tailor-made for that worldview. 

> **A note on complexity:** Dagster asks you to model assets and storage patterns up front; Prefect lets you move faster early and formalize later; Airflow sits in the middle—simple to start, but with a broad surface area once you scale.

---

## A Day in the Life of a Failing Pipeline

Let’s imagine S3 hiccups during ingestion:

-   **Airflow:** Task fails → retries per task policy. If a downstream task is queued but the **pool** is exhausted, priority weights decide what gets a worker slot first. Logs stream to your remote store for triage. **Deferrable sensors** don’t burn workers while waiting for buckets to reappear. 

-   **Prefect:** Task enters a failure state and retries; if the output was cached and the cache key still matches, retried tasks may short‑circuit. The run view shows per‑task states, and you can emit **artifacts** (e.g., “last successful checkpoint”) to help debug. **Tag-based concurrency limits** prevent a retry storm from stampeding the warehouse. 

-   **Dagster:** The asset failed to materialize; the UI flags the failed partition. You can kick off a **backfill** for only those broken partitions. Add or adjust **asset checks** to guard invariants (e.g., “no nulls in `order_id`”). Declarative automation can keep downstream assets from materializing until **blocking checks** pass.

---

## Common Misconceptions (and Reality Checks)

-   **“Airflow now does assets, so it’s the same as Dagster.”**
    Airflow’s **datasets** enable data-aware **triggers**, not first-class data storage semantics or automatic I/O. You still own how/where to persist and load data between tasks. 

-   **“Prefect replaces Spark/Ray/Dask.”**
    Prefect orchestrates; **task runners** can leverage threads/processes or submit to a Dask cluster. Heavy compute still runs in your compute engine of choice. 

-   **“Dagster is only for assets; ops/jobs are dead.”**
    Ops/jobs are still there for imperative workflows; assets are recommended when you’re producing durable data products. **Dynamic graphs** give you runtime flexibility even in op-based jobs.

---

## Historical Footnotes (why the ecosystems look like they do)

-   Airflow’s DAG-first model goes back to its origins; the **TaskFlow API** was introduced to make Pythonic DAGs easier and reduce operator boilerplate.
-   Prefect emphasized “negative engineering”—removing glue code around retries, timeouts, and conditional logic—hence the strong state machine and Python-first flows.
-   Dagster grew around an **asset** worldview: treat tables/files as first-class, design storage pluggability via **I/O managers**, and provide **declarative** rules for when an asset should update. 

---

## Practical Templates to Start From

### “One file per thing” Airflow project

-   `/dags/etl.py` (DAG+tasks)
-   `/include/` (SQL, scripts)
-   Airflow configs: set executor, remote logging, pools. 

### Prefect “notebook to prod”

-   `flows/etl.py` (flow+tasks)
-   `prefect.yaml` or CLI to build a **deployment** with parameters & schedule; create a **work pool** (“kubernetes”) and run a **worker** in the cluster. 

### Dagster “assets as code”

-   `src/<project>/assets.py` (assets + I/O manager)
-   `defs.py` (Definitions: assets, schedules, resources)
-   Optional: **asset checks** and **declarative automation** for freshness. 

---

## Summary: Matching Tool to Mental Model

-   Choose **Airflow** if you need a **DAG-first** orchestrator with broad operator coverage, mature scheduling, and many teams already familiar with it. Use **datasets** for data-aware triggers, **pools** for backpressure, and an **executor** that fits your infra. 
-   Choose **Prefect** if you want **Python-first flows** that feel like regular functions, with convenient concurrency via **task runners**, smooth local→deployment flow, **workers/work pools** for infra routing, and developer-friendly features like **artifacts** and **caching**. 
-   Choose **Dagster** if your north star is the **asset graph**—lineage, partitions, checks, and **declarative automation** driving materializations—backed by well‑designed **I/O managers** and strong observability of data products. 

In practice, all three can run the same pipelines. The difference is _how much of the platform you build yourself versus how much the tool gives you a vocabulary for_. DAGs, flows, or assets—pick the noun that makes your team fast.

---

## Further Reading

-   **Airflow**

    -   Architecture & core concepts, TaskFlow API, timetables, dynamic task mapping, datasets, pools, deferrable tasks, remote logs. 

-   **Prefect**

    -   Deployments/workers/work pools, flows/tasks, task runners & Dask, caching, artifacts, blocks, concurrency limits. 

-   **Dagster**

    -   OSS deployment architecture, code locations, run launchers/executors, I/O managers, schedules/sensors, declarative automation, dynamic graphs, partitions/backfills, asset checks.

---

### TL;DR

-   **Airflow**: If you think in _tasks_ and need battle‑tested scheduling across a large ecosystem.
-   **Prefect**: If you think in _functions_ and want orchestration to feel like writing Python.
-   **Dagster**: If you think in _assets_ and want lineage, checks, and data‑aware automation to be first‑class.
