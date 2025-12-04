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
    overlay_image: /assets/images/event-driven-migration/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/event-driven-migration/banner.png
title: "Zero‑Downtime Schema Evolution: Event‑Driven Migration with Debezium and Temporal"
tags:
    - event-driven migration
    - debezium
    - temporal
---

> As microservices mature, schema evolution and migration reliability are critical—this post dives deep into combining Debezium change streams with Temporal workflows to ensure database changes are atomic (in effect) and reversible.

---

## Why this matters (and why it’s hard)

Changing a live database is like moving furniture while the party is still going. Someone always needs a chair; someone else is standing exactly where you want the couch. You want to avoid stepping on toes (downtime), you want a plan if you drop something (rollback), and you want a way to coordinate helpers who arrive at different times (distributed services).

Traditional migrations (e.g., Flyway/Alembic scripts) are great for incremental DDL and small data fixes. But once a dataset grows or you need to transform rows at scale, the “take the app down for maintenance” playbook doesn’t cut it. You need:

-   **Zero downtime**: Readers and writers keep working during the change.
-   **Safety**: Every step is observable, retryable, and reversible.
-   **Coordination**: Multiple services switch behavior at the right moments.
-   **Proof**: You can prove the new shape matches the old shape before cutting over.

This post shows a concrete, production‑friendly pattern for achieving all four by pairing **Debezium** (change data capture) with **Temporal** (durable workflow orchestration). We’ll build up the approach, then walk through a realistic example: splitting a `users.name` column into `users.first_name` and `users.last_name` in PostgreSQL—without interrupting traffic.

---

## The two building blocks

### Debezium in 90 seconds

**Debezium** taps into your database’s transaction log (e.g., PostgreSQL’s WAL, MySQL’s binlog) and emits **ordered change events** (create, update, delete) for rows. You get a stream that includes “before” and “after” values, the operation (`c|u|d|r`), and source metadata (e.g., LSN/SCN). Debezium can snapshot existing data and then follow ongoing changes, writing events to Kafka (or other sinks). Key traits:

-   **At‑least‑once delivery** with **ordering per key**. Your consumer must be idempotent.
-   **Initial snapshot + incremental tailing** gives you a complete, replayable history window.
-   **Low coupling**: No triggers in your app schema; Debezium reads the log.

### Temporal in 90 seconds

**Temporal** lets you write workflows in normal code (Go, Java, TypeScript, etc.) that **survive process failures**. A workflow is deterministic; its state is **replayed from the event history** so it resumes exactly where it left off after crashes or deployments. Long‑running operations run as **activities** with automatic retries, heartbeating, and timeouts.

This makes Temporal perfect for orchestrating migrations:

-   **Gatekeeper**: Don’t progress to the next step until invariants hold.
-   **Sagas**: Define compensating actions for reversals.
-   **Human‑in‑the‑loop**: Pause at cutover points; advance via signals.
-   **Observability**: Every step is auditable with timestamps and results.

---

## The canonical pattern: Expand → Backfill → Switch → Contract

Most safe schema changes follow this rhythm:

1. **Expand**: Add new columns/tables/indices alongside old ones; keep the system backward/forward compatible. No behavior switches yet.
2. **Backfill**: Populate the new shape using a snapshot of existing data, then keep it in sync with live updates.
3. **Switch**:

    - **Reads**: Services start reading the new shape (often behind a flag).
    - **Writes**: Services dual‑write old and new shapes for a while, then write only the new.

4. **Contract**: Drop the old fields/tables once no consumer depends on them.

Debezium makes **backfill and sync** tractable; Temporal makes **ordering, gating, and rollback** tractable.

---

## Running example: Splitting `users.name` into `first_name` and `last_name`

Suppose your `users` table is:

```sql
CREATE TABLE public.users (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

You want:

```sql
ALTER TABLE public.users ADD COLUMN first_name TEXT;
ALTER TABLE public.users ADD COLUMN last_name TEXT;
```

And later you’ll enforce `first_name`/`last_name` as not null (after backfill), then drop `name`.

The catch: **millions of rows**, 24/7 traffic, multiple services reading/writing `users`.

---

## Architecture: Who does what?

**Data plane** (fast path):

-   **Application services** keep writing to `users.name` as before.
-   During “Switch (writes)”, they’ll dual‑write to `first_name/last_name`.

**Migration plane** (control + backfill):

-   **Debezium** streams `users` changes to Kafka.
-   A **Migration Worker** subscribes to those events, computes `(first_name, last_name)` from `name`, and **upserts** them into `users`.
-   A **Temporal Workflow** coordinates the life cycle: expand → backfill → switch → contract, with checks and compensation.

Think of Debezium + Migration Worker as a “real‑time, idempotent ETL” and Temporal as the conductor.

---

## Step‑by‑step implementation

### 1) Expand (DDL)

We start with reversible, metadata‑only changes (varies by DB/version). Add columns and any indices you know you’ll need.

```sql
-- Expand phase DDL (safe; no behavior change)
ALTER TABLE public.users ADD COLUMN first_name TEXT;
ALTER TABLE public.users ADD COLUMN last_name TEXT;

-- Optional: partial index or computed index you plan to use post-cutover
CREATE INDEX IF NOT EXISTS idx_users_last_name ON public.users (last_name);
```

> **Section recap**: We made the schema _superset‑compatible_. Nothing reads these columns yet.

---

### 2) Configure Debezium

A minimal PostgreSQL connector (via Kafka Connect) that watches `public.users`:

```json
{
    "name": "users-postgres-connector",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "plugin.name": "pgoutput",
        "database.hostname": "db",
        "database.port": "5432",
        "database.user": "debezium",
        "database.password": "******",
        "database.dbname": "app",
        "slot.name": "users_slot",
        "publication.autocreate.mode": "filtered",
        "table.include.list": "public.users",
        "topic.prefix": "cdc",
        "snapshot.mode": "initial",
        "include.schema.changes": "false",
        "tombstones.on.delete": "true",
        "heartbeat.interval.ms": "10000"
    }
}
```

This yields a topic like `cdc.public.users`. Each message key is the row’s PK; the value contains `before/after`, `op`, `ts_ms`, and source info.

> **Section recap**: Debezium will give us a consistent snapshot plus a live tail of row‑level changes.

---

### 3) Write the Migration Worker (CDC → upsert)

We’ll consume Debezium events and apply idempotent upserts. Here’s a TypeScript sketch using `kafkajs` and node‑pg:

```ts
// migration-worker/src/cdcConsumer.ts
import { Kafka, logLevel } from "kafkajs";
import { Pool } from "pg";

const kafka = new Kafka({
    clientId: "migration-worker",
    brokers: process.env.KAFKA_BROKERS!.split(","),
    logLevel: logLevel.INFO,
});

const pool = new Pool({ connectionString: process.env.PG_URL });

type DebeziumEnvelope<T> = {
    payload: {
        before: T | null;
        after: T | null;
        op: "c" | "u" | "d" | "r"; // create/update/delete/read(snapshot)
        ts_ms: number;
        source: { lsn?: string; txId?: string; table: string; db: string };
    };
};

type UserRow = { id: string; name: string | null };

function splitName(name: string | null): {
    first: string | null;
    last: string | null;
} {
    if (!name) return { first: null, last: null };
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return { first: parts[0], last: null }; // keep it lossy-safe
    const first = parts[0];
    const last = parts.slice(1).join(" ");
    return { first, last };
}

// Idempotent upsert using ON CONFLICT
const UPSERT_SQL = `
  UPDATE public.users
     SET first_name = COALESCE($2, first_name),
         last_name  = COALESCE($3, last_name),
         updated_at = now()
   WHERE id = $1
`;

async function handleEvent(env: DebeziumEnvelope<UserRow>) {
    const { op, after, before } = env.payload;

    if (op === "d") {
        // Deletion: nothing to backfill; you may want to cleanup or ignore.
        return;
    }

    const row = after ?? before;
    if (!row) return;

    const { first, last } = splitName(row.name);

    // Idempotent: sets columns to same values repeatedly if reprocessed.
    await pool.query(UPSERT_SQL, [row.id, first, last]);
}

export async function run() {
    const consumer = kafka.consumer({ groupId: "migration-users-name-split" });
    await consumer.connect();
    await consumer.subscribe({
        topic: "cdc.public.users",
        fromBeginning: true,
    });

    await consumer.run({
        eachMessage: async ({ message }) => {
            try {
                if (!message.value) return;
                const env = JSON.parse(
                    message.value.toString()
                ) as DebeziumEnvelope<UserRow>;
                await handleEvent(env);
            } catch (err) {
                // Let Kafka retry; if using Temporal activity, we'd surface failure metrics.
                console.error("CDC handler error", err);
                throw err;
            }
        },
    });
}

if (require.main === module)
    run().catch((e) => {
        console.error(e);
        process.exit(1);
    });
```

**Notes:**

-   We treat the stream as **at‑least‑once**. The upsert is idempotent.
-   We consume from the **beginning** to include the initial snapshot. After catch‑up, we’ll be near real time.

> **Section recap**: Any change to `users.name` (new users or updates) drives an upsert into `first_name/last_name`.

---

### 4) Orchestrate with Temporal

Temporal’s job is to **sequence** the steps, **enforce invariants**, and provide **rollback**. We’ll show TypeScript (Node SDK). Pattern:

-   Each phase is an **activity** (external side effects, retries).
-   The workflow **awaits signals** for human approvals at cutover points.
-   Failures trigger **compensation** (Saga) in reverse order.

#### Workflow contract

```ts
// temporal/workflows/migrateUsersNameSplit.ts
import {
    proxyActivities,
    defineSignal,
    setHandler,
    condition,
} from "@temporalio/workflow";
import type * as Acts from "../activities";

const {
    expandSchema,
    ensureDebeziumConnector,
    ensureMigrationWorker,
    waitForCatchup,
    enableReadFlag,
    enableDualWriteFlag,
    verifyReadParity,
    disableOldReads,
    disableOldWrites,
    dropOldColumn,
    makeNewColumnsNotNull,
} = proxyActivities<typeof Acts>({
    startToCloseTimeout: "10 minutes",
    retry: { maximumAttempts: 0 }, // Let activities implement their own retry when appropriate
});

export const approveCutover = defineSignal("approveCutover"); // human gate
export const approveContract = defineSignal("approveContract"); // human gate

export async function migrateUsersNameSplitWorkflow() {
    // 1) Expand
    await expandSchema(); // ALTER TABLE add columns; safe

    // 2) CDC backfill
    await ensureDebeziumConnector(); // idempotent: PUT connector if absent
    await ensureMigrationWorker(); // ensure deployment/healthchecks
    await waitForCatchup({ maxLagSeconds: 30, minStableSeconds: 120 });

    // Optional: make new columns NOT NULL once fully backfilled and stable
    await makeNewColumnsNotNull(); // still no behavior switch

    // 3) Switch Reads (human-approved)
    let cutoverApproved = false;
    setHandler(approveCutover, () => {
        cutoverApproved = true;
    });
    await condition(() => cutoverApproved);

    await enableReadFlag(); // services start reading first/last (dual-read)
    await verifyReadParity(); // compare results vs old name parsing; raise alarm on drift

    // 4) Switch Writes
    await enableDualWriteFlag(); // services write both name and first/last
    await waitForCatchup({ maxLagSeconds: 5, minStableSeconds: 60 }); // stabilize

    // Optional: stop writing legacy field in app (another gate or TTL)
    await disableOldWrites();

    // 5) Contract (human-approved)
    let contractApproved = false;
    setHandler(approveContract, () => {
        contractApproved = true;
    });
    await condition(() => contractApproved);

    await disableOldReads(); // remove old read path/flag in app
    await dropOldColumn(); // ALTER TABLE DROP COLUMN name
}
```

#### Activities (sketches)

```ts
// temporal/activities/index.ts
import { Client } from "pg";
import fetch from "node-fetch";

const pg = new Client({ connectionString: process.env.PG_URL! });

export async function expandSchema() {
    await pg.connect();
    try {
        await pg.query(
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS first_name TEXT"
        );
        await pg.query(
            "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_name TEXT"
        );
    } finally {
        await pg.end();
    }
}

export async function ensureDebeziumConnector() {
    // Idempotently upsert the connector via Kafka Connect REST
    const body = {
        /* same JSON as above */
    };
    const resp = await fetch(
        `${process.env.CONNECT_URL}/connectors/users-postgres-connector/config`,
        {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        }
    );
    if (!resp.ok)
        throw new Error(`Debezium connector upsert failed: ${resp.status}`);
}

export async function ensureMigrationWorker() {
    // Ensure the worker Deployment exists and is healthy (K8s API or internal healthcheck).
    // In practice: check /healthz on the service; create if missing.
}

export async function waitForCatchup(opts: {
    maxLagSeconds: number;
    minStableSeconds: number;
}) {
    // Poll consumer group lag metrics (Kafka) and Debezium heartbeat events.
    // Wait until lag < maxLagSeconds for minStableSeconds consecutively.
}

export async function makeNewColumnsNotNull() {
    await pg.connect();
    try {
        // Validate: no nulls remain
        const { rows } = await pg.query(
            "SELECT COUNT(*) AS c FROM public.users WHERE first_name IS NULL OR last_name IS NULL"
        );
        if (Number(rows[0].c) > 0)
            throw new Error("Nulls remain; cannot enforce NOT NULL");
        // Optional: enforce constraints
        // await pg.query('ALTER TABLE public.users ALTER COLUMN first_name SET NOT NULL');
        // await pg.query('ALTER TABLE public.users ALTER COLUMN last_name SET NOT NULL');
    } finally {
        await pg.end();
    }
}

export async function enableReadFlag() {
    // Toggle a feature flag (internal config service) to start reading new columns
}

export async function verifyReadParity() {
    // Compare sampled queries: SELECT name vs concat_ws(' ', first_name, last_name)
    // Emit metrics and fail if mismatch > threshold
}

export async function enableDualWriteFlag() {
    // App writes to both name and first/last. Temporal shouldn't flip writes
    // until verifyReadParity is consistently good.
}

export async function disableOldWrites() {
    // Flip flag to stop writing legacy 'name'
}

export async function disableOldReads() {
    // Remove old read path
}

export async function dropOldColumn() {
    await pg.connect();
    try {
        await pg.query("ALTER TABLE public.users DROP COLUMN IF EXISTS name");
    } finally {
        await pg.end();
    }
}
```

> **Section recap**: The workflow sequences the migration and blocks on safety checks and approvals. Each side effect is isolated in an activity that can be retried or compensated.

---

### 5) Making it reversible with Sagas

Not every step has a perfect “inverse,” but many do. Temporal doesn’t impose a saga API—you can implement one in your workflow:

```ts
// temporal/workflows/saga.ts (inline idea)
class Saga {
    private steps: Array<() => Promise<void>> = [];
    add(compensator: () => Promise<void>) {
        this.steps.push(compensator);
    }
    async compensate() {
        for (const c of this.steps.reverse()) await c();
    }
}

// Using it inside the workflow:
const saga = new Saga();
try {
    await expandSchema(); // No compensation needed (safe to leave)
    await ensureDebeziumConnector();
    saga.add(async () => {
        /* remove connector or stop it */
    });

    await ensureMigrationWorker();
    saga.add(async () => {
        /* scale to zero worker */
    });

    await enableReadFlag();
    saga.add(async () => {
        /* disableReadFlag */
    });

    await enableDualWriteFlag();
    saga.add(async () => {
        /* disableDualWriteFlag */
    });

    // ...
    // Final irreversible step:
    await dropOldColumn(); // no compensation beyond restoring from backups
} catch (err) {
    await saga.compensate();
    throw err;
}
```

If **verifyReadParity** fails late in the game, Temporal rolls the flags back, stops the worker, and leaves the database in a known good state—without anyone SSH’ing into production at 2 a.m.

> **Section recap**: A Saga gives you a first‑class escape hatch; failures unwind to safety.

---

## Verification: proving safety before switching

For a schema change to be “effectively atomic,” you need **evidence** at each gate:

-   **Backfill completed**: Count checks (number of rows without `first_name/last_name` is zero), streaming **lag** is below threshold, and **stays** below for a window.
-   **Read parity**: Sample compare `(name)` vs `concat_ws(' ', first_name, last_name)` across hot partitions, record **mismatch rate**, block on zero or near‑zero (depending on your tolerance).
-   **Dual writes**: Confirm app logs/metrics for dual‑writes are non‑erroring and the migration worker lag remains low.
-   **Post‑cutover monitoring**: After disabling old writes, watch for debounced increases in errors; keep rollback open for a cooldown period.

Temporal can encode these as **activity preconditions** with timeouts and exponential backoff.

---

## Practical concerns & edge cases

### “Add column” rewrites data?

Some DDL is **metadata‑only** (fast), some rewrites the table (slow, locks). The pattern above **hides** that complexity: do slow DDL in the **Expand** phase days in advance during low traffic, then only **Switch** at a safe moment. Your DBA (or test cluster) will tell you whether a particular DDL is safe for your engine/version.

### Primary key changes

CDC on PK changes produces an `UPDATE` with `before` and `after` keys. Ensure your consumer uses the **value**’s current `id` (or merges with `before`’s PK) so the upsert hits the right row.

### Deletes and tombstones

For deletions (`op='d'`) you may not need to do anything for backfill; the row is gone. If you maintain a shadow table, ensure you **cascade** or delete there as well. With Kafka compaction, Debezium can emit tombstones—your consumer should ignore or use them to clean state.

### Long‑running transactions

Debezium emits changes **after commit**. A huge transaction can delay visibility; monitor CDC lag and use Temporal’s `waitForCatchup` to gate cutover until lag is small and stable.

### Idempotency (trust, but verify)

Never assume a single delivery. All activities must be **idempotent**:

-   DDL uses `IF NOT EXISTS`.
-   Connector deployment is a **PUT** (upsert).
-   Upserts use `INSERT ... ON CONFLICT DO UPDATE` or `UPDATE` keyed by PK.
-   Feature flags are **set-to-value**, not toggled.

### Clock skew and consistency windows

Use **source LSN/SCN** or `ts_ms` to reason about catch‑up rather than wall clock. In practice, **consumer group lag** + Debezium heartbeat is a good proxy. Don’t switch until lag is under a small threshold for several consecutive checks.

### Large backfills (terabytes)

-   Use Debezium’s **incremental snapshots** to avoid long exclusive locks.
-   Throttle the migration worker (max in‑flight, batch size).
-   Prefer **bulk upserts** (batch `UPDATE`) for snapshot phase; switch to row‑by‑row for the tail.
-   Consider **partitioned tables** and run per‑partition child workflows for parallelism, each with its own catch‑up gate.

### What about renames?

True renames are just **expand** (add new), **dual‑write**, **switch**, **contract** (drop old). A pure `ALTER TABLE RENAME COLUMN` is alluring but breaks old readers. Prefer the pattern even for “simple” renames—your future self will thank you.

### Online DDL tools

Tools like `gh-ost` or `pt-online-schema-change` help with table rewrites without long locks. They fit nicely in the **Expand** phase if you need to reshape a large table. Temporal can wrap them in activities with timeouts and compensation.

---

## Observability and runbooks

**Metrics to emit** (from the worker and activities):

-   **CDC lag** (seconds and records).
-   **Rows remaining** in backfill (`NULL` count on new columns).
-   **Parity mismatch rate** during dual‑read.
-   **Activity attempts**, **retry counts**, **durations**, **timeouts**.
-   **Human approvals** captured as signals with timestamps.
-   **Cutover duration** and **post‑cutover error rate**.

**Dashboards**: Put these on a single page linked from the workflow run. Make “go/no‑go” obvious.

**Runbooks**:

-   _Abort during Expand_: safe—DDL can stay; connector/worker can be stopped.
-   _Abort during Backfill_: stop the worker; connector can remain idle; safe to resume.
-   _Abort after dual‑write enabled_: **compensate** by disabling dual‑write and read flags; let CDC drain; investigate parity mismatches.
-   _Abort after drop_: Only option is re‑expand and re‑migrate from backups—hence we delay drops and require human approval.

---

## Variations on the theme

### Splitting a table

Instead of columns, you might move optional fields into a new `user_profiles` table:

-   **Expand**: create `user_profiles(id PK, user_id FK, ...)`.
-   **Backfill**: CDC worker creates/upserts profile rows.
-   **Switch**: services start reading from `JOIN` and dual‑write; later write only to `user_profiles`.
-   **Contract**: drop old columns from `users`.

### Type changes and normalization

Changing a `status TEXT` with free‑form values to an enum? Expand with a new `status_code INT`, backfill with a mapping function, dual‑write (ensure the app uses the mapping), switch reads to enum, then drop old text.

### Cross‑service migrations

If two or more services consume the same table, Temporal can:

-   Signal **each service’s workflow** (or activity) to flip flags in a safe order.
-   Wait on **queries** that report the live rollout percentage (e.g., from a config service) before proceeding.

---

## A quick end‑to‑end transcript

1. **Start workflow** `migrateUsersNameSplitWorkflow`.
2. **expandSchema** runs: columns added.
3. **ensureDebeziumConnector** upserts the connector.
4. **ensureMigrationWorker** deploys worker; worker begins consuming from the start.
5. **waitForCatchup** detects lag near zero for 2 minutes; snapshot + tail complete.
6. **makeNewColumnsNotNull** validates zero nulls; enforces constraints (optional).
7. Ops reviews dashboards, sends **approveCutover** signal.
8. Temporal **enableReadFlag**; services read from `first_name/last_name` (keep reading `name` for parity).
9. **verifyReadParity** runs continuously; zero mismatches.
10. **enableDualWriteFlag**; apps write both `name` and `first/last`.
11. **waitForCatchup**; CDC lag stable; no errors.
12. **disableOldWrites** flips app to stop writing `name`.
13. Ops reviews, sends **approveContract**.
14. **disableOldReads** and **dropOldColumn** finalize the change.

Total production impact: no downtime, clear gates, and built‑in reversibility until the final drop.

---

## Design choices that make this robust

-   **Treat migration as a product**: version it, test it, ship it through environments.
-   **Idempotency everywhere**: especially in CDC consumers and activities.
-   **Deterministic workflows**: avoid reading the world directly in a workflow; push side effects into activities.
-   **Human‑in‑the‑loop at cutovers**: automation proves safety; humans accept the last step.
-   **Delayed contraction**: keep legacy fields long enough to sleep easy (days, not minutes).
-   **Compare at the edge**: parity checks happen in the read path (or a shadow read) where users actually experience data.

---

## Frequently asked questions

**Do I have to use Kafka?**
Debezium commonly uses Kafka Connect, but it also supports other sinks and an embedded engine. Kafka gives you durability, offset management, and metrics that make **waitForCatchup** easy.

**Isn’t this overkill for “small” migrations?**
Yes. For a small, safe DDL on a tiny table, a regular migration tool is fine. Reach for Debezium + Temporal when (a) the dataset is large, (b) backfill logic is non‑trivial, (c) multiple services must switch in lockstep, or (d) you need a clean rollback story.

**How is this “atomic”?**
We achieve **effective atomicity** at the product level by gating user‑visible changes behind flags and checks. The database operations themselves are not one big transaction; the **workflow** ensures no user sees a half‑migrated state.

**What about security (PII) in CDC streams?**
Debezium supports **field masking** and **topic routing**. You can also have the worker strip or hash sensitive values immediately. Keep topics private and ACL’d.

---

## Summary

-   **Debezium** turns your live database into a reliable, ordered event stream—perfect for backfills that keep up with ongoing writes.
-   **Temporal** turns your migration into a durable, observable, and reversible _process_—perfect for orchestrating checks, approvals, retries, and compensation.
-   Together they implement the proven **Expand → Backfill → Switch → Contract** dance with zero downtime, confidence at each step, and a clear story when things go sideways.

This pattern scales—from renaming a column to splitting a monolithic table—because it makes correctness observable and progress controllable.

---

## Further reading & ideas to explore

-   Debezium docs on snapshots, incremental snapshots, and heartbeat topics.
-   Temporal docs on workflows, activities, signals/queries, and workflow versioning.
-   The Saga pattern for long‑running, multi‑step changes.
-   Online DDL tools (e.g., gh-ost, pt-osc) for big table rewrites in the **Expand** phase.
-   The Outbox pattern for propagating domain events with CDC (complementary to schema migration).

