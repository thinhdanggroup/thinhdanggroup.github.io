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
    overlay_image: /assets/images/sqlite-serverless-backend/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/sqlite-serverless-backend/banner.png
title: "How SQLite Is Powering the New Generation of Serverless Backends"
tags:
    - sqlite
    - serverless
---

If you’d told me a few years ago that _SQLite_ would be at the center of “planet-scale” serverless architectures, I would’ve assumed you were trolling.

SQLite was the thing you used for:

-   quick prototypes
-   mobile apps
-   random side projects where “real database” meant “I’ll migrate to Postgres later”

Fast‑forward to 2025 and suddenly:

-   **Turso/libSQL** is marketing microsecond‑level queries with embedded replicas and global edge distribution. ([Turso][1])
-   **Cloudflare D1** is “a serverless SQL database with SQLite semantics” that can replicate reads worldwide and plug directly into Workers. ([Cloudflare Docs][2])
-   **LiteFS** lets you run SQLite on each node of your cluster and quietly replicates everything for you via a distributed filesystem. ([Fly][3])

SQLite didn’t change that much. What changed is how we _wrap it_.

This post is a deep dive into **why SQLite is suddenly a fantastic fit for serverless backends**, and how tools like Turso/libSQL, Cloudflare D1, and LiteFS are turning a single‑file database engine into globally distributed infrastructure.

---

## 1. Serverless and Databases: The Old Awkward Relationship

Let’s start with the classic serverless story:

1. You deploy a bunch of stateless functions (Lambda, Workers, Vercel Functions, etc.).
2. Each function runs in short bursts, spins up and down on demand, and can appear in **many regions**.
3. You need a relational database. You reach for Postgres or MySQL.

And now the fun begins:

-   Every cold start may need to **establish a new TCP connection** to the DB.
-   Hundreds or thousands of concurrent functions might each need a connection, so you bolt on **connection pooling proxies** (RDS Proxy, PgBouncer, PgBouncer‑for‑PgBouncer…).
-   If you deploy your functions globally but your DB is in one region, latency spikes for users far from that region.
-   Multi‑region writes, if you try to go there, quickly turn into “I did not sign up to build Spanner”.

In short: serverless functions are **ephemeral and distributed**, while traditional SQL databases are **long‑lived and centralized**. Getting them to play nicely usually means paying for a lot of always‑on infrastructure and operational complexity.

Now enter SQLite.

---

## 2. Why SQLite, of All Things?

SQLite’s design looks almost tailor‑made for serverless:

-   It’s **embedded**: your app links a library, and the database is just a file on disk.
-   There’s no separate server to manage, no sockets, no authentication layer by default.
-   Reads are basically **syscalls and memory copies** instead of network round‑trips.
-   It’s surprisingly capable: full SQL, transactions, indexing, foreign keys, etc.

Historically this made SQLite perfect for **single‑node** workloads (mobile, desktop, tiny servers). But it had a big caveat:

> Classic SQLite is not a networked, multi‑writer database.

There’s **one main database file**, and while you can have many concurrent readers, there’s effectively **a single writer at a time**. Great for simplicity and reliability; not great if you naïvely try to hit the same file from 20 Kubernetes pods over NFS.

So how the hell are Turso, D1, and LiteFS using it to power **distributed** and **serverless** backends?

The trick is **not** to turn SQLite into Postgres. The trick is to **let SQLite stay SQLite**—a fast, embedded, single‑file database engine—and build the distributed system _around_ it.

Concretely, most of these systems follow a pattern:

1. Designate one place as the **primary writer**.
2. Treat SQLite’s **Write‑Ahead Log (WAL)** as an authoritative stream of changes.
3. Ship WAL frames (or page‑level diffs) to other nodes.
4. Apply them to **local replicas**, so every node has its own SQLite file to read from.

In other words, they build a **database CDN** on top of SQLite.

Let’s look at how that plays out in practice.

---

## 3. Turso & libSQL: SQLite as a Distributed Edge Service

### 3.1 What is libSQL?

**libSQL** is a community‑driven fork of SQLite created by the Turso team to turn SQLite into “SQLite for modern applications.” It keeps SQLite’s file format and SQL dialect but adds things SQLite doesn’t want to bake in itself: replication, server mode, WebAssembly support, and more. ([GitHub][4])

Turso is then built on libSQL as a **managed, globally distributed edge database**: you get SQLite semantics with low‑latency access from edge runtimes and geographically close replicas. ([Backova][5])

Key features we care about:

-   **Server mode**: you can talk to libSQL over HTTP/WebSockets from serverless runtimes.
-   **Replication**: write to a primary; replicas stay in sync.
-   **Embedded replicas**: this is where it gets really interesting.

### 3.2 Embedded replicas: SQLite _in_ your app, synced to the cloud

An **embedded replica** is literally a **local SQLite file** inside your app (on a VM, container, etc.) that automatically syncs from a remote Turso/libSQL database. Reads come from the local file; writes go to the remote primary and then flow back down to update the local file. ([Turso Docs][6])

From Turso’s docs and blog posts, the flow is roughly:

1. Primary (in Turso Cloud) is the **source of truth**.
2. Every write updates the primary and appends frames to a **replication log** built on top of SQLite’s WAL. ([Into the Stack][7])
3. Embedded replicas periodically fetch those WAL frames and apply them locally, updating their own SQLite file.
4. Your app now has **zero‑latency local reads** and can still treat the cloud DB as the canonical store.

You can even configure offline modes where your embedded replica accepts local writes and syncs when connectivity is restored. ([Turso Docs][6])

### 3.3 What this looks like in code (TypeScript / serverless)

Here’s a minimal example using `@libsql/client` in a TypeScript app that could run in a serverless function. First, we just connect directly to a remote Turso database: ([Turso Docs][8])

```ts
// db.ts
import { createClient } from "@libsql/client";

export const db = createClient({
    url: process.env.TURSO_DATABASE_URL!, // e.g. libsql://my-db-123.turso.io
    authToken: process.env.TURSO_AUTH_TOKEN!, // generated via `turso db tokens create`
});
```

Querying it from, say, a Next.js route handler:

```ts
// app/api/posts/route.ts
import { db } from "@/db";

export async function GET() {
    const result = await db.execute(
        "SELECT id, title FROM posts ORDER BY created_at DESC"
    );
    return Response.json(result.rows);
}
```

That alone gives you a **multi‑region, managed SQLite** backend with Turso taking care of global replicas in their edge network. ([Backova][5])

Now let’s switch on an **embedded replica** on a VM or long‑lived container:

```ts
// db-embedded.ts
import { createClient } from "@libsql/client";

export const db = createClient({
    // Local file on disk — SQLite as usual:
    url: "file:local.db",
    // Remote primary to sync from:
    syncUrl: process.env.TURSO_DATABASE_URL!,
    authToken: process.env.TURSO_AUTH_TOKEN!,
    // Sync every 60 seconds:
    syncInterval: 60,
});
```

Reads go against `local.db` (no network hop), and behind the scenes libSQL periodically syncs from the primary. ([Turso Database][9])

For a serverless‑y architecture (for example, an edge API hosted on a platform that gives you a small persistent disk), this is wild:

-   Your function **talks to a local SQLite file** most of the time.
-   That file stays in sync with a canonical cloud database.
-   You don’t manage replication logic yourself; you just treat it as “SQLite, but synced.”

Turso’s own “DIY database CDN” posts describe how this can eliminate the need for many multi‑region replicas because your app’s own nodes act as replicas. ([Turso][10])

---

## 4. Cloudflare D1: Serverless SQLite with a Global Control Plane

Turso/libSQL gives you a “SQLite‑plus‑replication” engine you can use anywhere. **Cloudflare D1** goes a step further and makes _the whole thing_ look like a native serverless platform feature.

### 4.1 D1 as a managed serverless SQLite

D1 is Cloudflare’s **managed, serverless SQL database** that “understands SQLite semantics,” integrates with Workers via bindings, and exposes both a Worker API and HTTP/REST interface. ([Cloudflare Docs][2])

The high‑level promise:

-   **No database server to run.** You create a D1 instance via CLI or dashboard.
-   **Direct integration with Workers.** Your Worker gets an `env.DB` binding of type `D1Database`. ([Cloudflare Docs][11])
-   **Serverless billing model.** You pay based on queries/storage, not an always‑on VM. ([Cloudflare Workers][12])

### 4.2 Global read replication and the Sessions API

The more interesting bit for our serverless story: D1 now supports **global read replication**. Writes go to a primary; **read replicas** are deployed in other regions to handle local reads with lower latency. ([Cloudflare Docs][13])

To keep things consistent, Cloudflare introduces the **D1 Sessions API**:

-   You create a session via `env.DB.withSession(...)`.
-   All queries in that session share a **sequential consistency** guarantee: they see changes in a consistent order, even if routed to different replicas. ([Cloudflare Docs][13])
-   Sessions carry a **bookmark** (a logical version of the database) so D1 can ensure a replica is up‑to‑date enough before serving a query. ([Cloudflare Docs][11])

This is important because it gives you a simple mental model:

-   Reads for a given user/session are consistent.
-   You don’t need to manually reason about which region is “safe” to hit.

### 4.3 What it looks like in a Worker

Basic Worker querying D1 without sessions (single region / no replication):

```ts
export default {
    async fetch(request: Request, env: Env) {
        // DB is a D1 binding defined in wrangler.toml
        const stmt = env.DB.prepare(
            "SELECT id, title, created_at FROM posts ORDER BY created_at DESC LIMIT ?"
        ).bind(20);

        const { results } = await stmt.all();
        return Response.json(results);
    },
};
```

Here `env.DB` is a `D1Database`; `prepare().bind().all()` is the standard pattern from the Worker Binding API. ([Cloudflare Docs][11])

Now, the same thing using a **session** so read replication can kick in:

```ts
export default {
    async fetch(request: Request, env: Env) {
        // Start a session; "first-unconstrained" favors lowest latency for the first query.
        const session = env.DB.withSession("first-unconstrained");

        const { results } = await session
            .prepare(
                "SELECT id, title, created_at FROM posts ORDER BY created_at DESC LIMIT ?"
            )
            .bind(20)
            .all();

        // Optionally return a bookmark to the client if you want them to resume from here
        const bookmark = session.getBookmark();

        return Response.json({ posts: results, bookmark });
    },
};
```

Behind the scenes, D1 handles:

-   where your primary lives
-   how replicas are placed
-   how to route session queries to instances that respect your consistency needs ([The Cloudflare Blog][14])

As a serverless developer, you’re simply talking to “SQLite with a global control plane.”

---

## 5. LiteFS: A Distributed Filesystem That Replicates SQLite

Turso/libSQL and D1 are “database as a service” products. **LiteFS**, from Fly.io, takes a different angle: it’s a **distributed filesystem** designed specifically to replicate SQLite databases across nodes. ([Fly][3])

The core idea:

1. You mount a LiteFS filesystem (FUSE) and point your app’s SQLite database path into it.
2. LiteFS **intercepts writes** to the DB file, groups them into transaction log files (LTX files), and sends them to replicas. ([Fly][15])
3. Each replica applies LTX files in order, maintaining its own local copy of the database.
4. Leader/primary election is handled via **Consul leases** rather than a heavy consensus layer like Raft. ([GitHub][16])

From SQLite’s point of view, it’s just reading/writing a local file; LiteFS does all the replication work underneath.

This is ideal when:

-   you’re already running on something like Fly.io or Kubernetes
-   you want **SQLite right next to your app** in every region
-   you want high availability and failover for your DB without switching to a separate DB engine

A very trimmed‑down Fly + LiteFS mental architecture:

-   One **primary** Fly VM where writes are allowed.
-   Several **replica** VMs where the DB dir is mounted read‑only via LiteFS.
-   Your app runs on every VM, always reading from its local SQLite file; writes are automatically forwarded to the node that currently holds the primary lease. ([Fly][15])

To your HTTP handlers, this still feels like **“use SQLite normally”**, but you get transparent read scaling and failover.

---

## 6. Common Pattern: Make SQLite Look Like a Networked, Global DB

If you squint a little, Turso/libSQL, D1, and LiteFS are all doing variations of the same thing:

1. **Keep SQLite as the storage engine.**
   They rely on SQLite’s durability and file format.

2. **Single‑writer, replicated‑readers model.**
   There’s a primary that gets all writes; replicas get WAL or transaction stream data and apply it locally. ([Into the Stack][7])

3. **Local reads, network writes.**
   Reads stay in‑process (or at least in‑region); writes pay the cross‑region hop.

4. **A control plane on top.**

    - Turso/libSQL: replication endpoints, embedded replica sync intervals, auth tokens, etc. ([Turso Docs][17])
    - D1: global placement, Sessions API, bookmarks. ([Cloudflare Docs][18])
    - LiteFS: leader election, Consul leases, transaction logs. ([GitHub][16])

In all three cases, your code is “just” doing SQL queries. But under the hood, a surprisingly sophisticated distributed system is:

-   capturing WAL pages
-   shipping them around
-   replaying them in order
-   dealing with failures and promotion of new primaries

And all of this without you provisioning a classic database cluster.

---

## 7. Designing a Serverless Backend on SQLite Today

Let’s make this concrete with two example architectures.

### 7.1 Next.js + Turso (libSQL) on a serverless/edge platform

**Goal**: Low‑latency reads everywhere, simple writes, minimal ops.

**Ingredients:**

-   Next.js app deployed on a serverless/edge platform (e.g., Vercel, Netlify, etc.)
-   Turso database with global replicas
-   `@libsql/client` in your app runtime ([Turso Docs][8])

**Pattern:**

-   In **API routes / Server Components**, initialize a single `db` client per runtime instance (or use module‑level singleton).
-   For latency, either:

    -   rely on Turso’s **edge‑hosted replicas** near your functions, or
    -   use **embedded replicas** if the platform gives you persistence on the instance and allows file access.

Write handler example:

```ts
// app/api/posts/route.ts
import { db } from "@/db";

export async function POST(request: Request) {
    const body = await request.json();
    const { title, content } = body;

    await db.execute({
        sql: "INSERT INTO posts (title, content) VALUES (?, ?)",
        args: [title, content],
    });

    return new Response(null, { status: 201 });
}
```

Read handler stays exactly the same as any other SQL DB, but now:

-   Reads are served from a nearby edge location (or embedded replica).
-   Writes go to the primary region and fan out via replication.

### 7.2 Cloudflare Workers + D1 + Sessions

**Goal**: Fully serverless backend with global reads and per‑session consistency.

**Pattern:**

-   Define a D1 binding in `wrangler.toml` (e.g., `DB`).
-   In your Worker, create a session per logical user (e.g., per cookie or per API token).
-   Use that session for all queries to get consistent reads while benefiting from read replicas. ([Cloudflare Docs][13])

Example:

```ts
export default {
    async fetch(request: Request, env: Env) {
        const url = new URL(request.url);
        const userId = url.searchParams.get("user") ?? "anonymous";

        // You might hash userId into a session key; here we just use it directly.
        const session = env.DB.withSession("first-unconstrained");

        const { results } = await session
            .prepare(
                "SELECT * FROM todos WHERE user_id = ? ORDER BY created_at DESC"
            )
            .bind(userId)
            .all();

        const bookmark = session.getBookmark();

        return Response.json({ todos: results, bookmark });
    },
};
```

This gives you:

-   **SQLite semantics** (same SQL dialect, transaction behavior). ([Cloudflare Docs][2])
-   **Serverless ops model** (D1 is fully managed).
-   **Global reads with low latency** via D1’s replication, without you manually sharding or routing.

---

## 8. Why This Works So Well for Serverless

So what makes “distributed SQLite” such a good fit for serverless backends?

### 8.1 Operational simplicity

Instead of:

-   a separate DB cluster
-   connection pools and proxies
-   custom multi‑region networking

You get:

-   a **library** (libSQL, SQLite) or **binding** (D1) you use directly from your code
-   either no connections at all (embedded) or relatively lightweight HTTP/WebSocket connections, which play nicer with ephemeral compute

This aligns perfectly with serverless philosophy: **scale the platform, not the user’s ops brain.**

### 8.2 Economics

Traditional managed SQL often comes with a **minimum cost floor**: you’re paying for at least one always‑on server, sometimes more. Even if your traffic is spiky or tiny, you rarely get to “scale to zero” economically.

Serverless‑styled SQLite services can:

-   run as **multi‑tenant** infrastructure under the hood
-   charge you per usage, storage, and replication features rather than per VM

Cloudflare explicitly markets D1 as cost‑effective for “creating a serverless relational database in seconds,” and Turso emphasizes lightweight edge replicas rather than heavy regional instances. ([Cloudflare Workers][12])

### 8.3 Latency and the edge

When your compute is everywhere, your data wants to be everywhere too. SQLite is uniquely suited to this because it’s:

-   tiny
-   file‑based
-   fast on local disks

Using either embedded replicas (Turso/libSQL), D1 read replicas, or LiteFS nodes, your **read path** becomes “hit the closest SQLite file” and your **write path** becomes “ship this transaction to the primary.” ([Turso][19])

That’s a very simple mental model for application developers.

---

## 9. Trade‑offs and When Not to Use SQLite‑as‑Backend

Nothing is free. These systems _do_ have limitations you should be aware of.

### 9.1 Write scalability

Most of these architectures are **single‑primary**:

-   Turso/libSQL: one primary, many replicas (embedded or remote). ([Into the Stack][7])
-   D1: one primary, replicated readers. ([Cloudflare Docs][13])
-   LiteFS: a primary node holding the write lease, others are read‑only. ([GitHub][16])

That’s fine for **typical web traffic** (lots of reads, modest writes), but if you need:

-   extremely high write throughput
-   multi‑primary writes across continents

you’re now in the same territory as any other strongly consistent distributed SQL system: you’ll probably want something purpose‑built (CockroachDB, Yugabyte, Spanner, etc.).

### 9.2 Multi‑region write patterns are opinionated

Because these systems funnel writes through a primary, patterns like:

-   “Users in each region write only to that region, with cross‑region conflict resolution”

are not the sweet spot. They push you toward **global ordering** rather than conflict‑free replication.

For many SaaS apps, that’s fine. For collaborative editing across continents with super tight latency, you might mix in CRDTs or another layer.

### 9.3 SQLite constraints still apply

Recall that:

-   SQLite has a **single writer** per database file, even on a single node. That’s ok when writes are small & fast; less ok for long‑running transactions.
-   Some advanced features (e.g., certain extensions, exotic isolation patterns) may not be available or may behave differently in replicated setups.
-   Using WAL mode correctly with these tools sometimes has caveats (e.g., LiteFS relies on the locking protocol; certain locking modes can confuse it). ([GitHub][20])

The good news: most frameworks + ORMs (Drizzle, Prisma in specific modes, ORMs via HTTP adapters) already have D1/Turso drivers or patterns emerging. ([PyPI][21])

---

## 10. Key Takeaways

Let’s recap the “aha” moments:

-   **SQLite hasn’t become a distributed database by itself.**
    It’s the same embeddable, single‑file engine — but people are now treating its WAL as a **replication log** and wrapping it with distributed systems logic. ([Into the Stack][7])

-   **Turso/libSQL** turn SQLite into a **networked, replicated service** with embedded replicas so you can literally have a synced SQLite file inside your app, plus cloud primaries and edge distribution. ([Turso Docs][17])

-   **Cloudflare D1** gives you a **fully managed serverless database** with SQLite semantics, Worker bindings, and global read replication via sessions and bookmarks. ([Cloudflare Docs][2])

-   **LiteFS** replicates SQLite at the filesystem level, so each node in your cluster gets a **local SQLite file** with state mirrored from the primary, using Consul‑based leases for leader election. ([Fly][15])

-   For serverless backends, this means:

    -   **No heavy DB cluster management** for a huge class of apps.
    -   Low‑latency reads everywhere via local SQLite replicas.
    -   Economics that fit “scale to zero” workloads much better than always‑on DB instances.

The biggest shift is mental: instead of thinking “SQLite is for toys and mobile apps,” you can think:

> “SQLite is my high‑performance storage engine. The real question is which **replication wrapper** I want around it for my backend.”

---

## 11. Further Reading

If you want to go deeper, here are some great jumping‑off points:

-   **SQLite & Edge Databases**

    -   _“SQLite Is Eating the Cloud in 2025”_ – a broad overview of edge SQLite patterns (Turso, D1, LiteFS, Litestream). ([debugg.ai][22])

-   **Turso / libSQL**

    -   Turso docs on libSQL and architecture. ([Turso Docs][17])
    -   “Microsecond‑level SQL query latency with libSQL local replicas.” ([Turso][1])
    -   “Introducing Embedded Replicas: Deploy Turso anywhere” and “Local‑First SQLite, Cloud‑Connected with Turso Embedded Replicas.” ([Turso][23])

-   **Cloudflare D1**

    -   D1 Getting Started + Worker Binding API docs. ([Cloudflare Docs][24])
    -   “Sequential consistency without borders: how D1 implements global read replication.” ([The Cloudflare Blog][14])

-   **LiteFS**

    -   LiteFS docs: “LiteFS – Distributed SQLite” and “How LiteFS Works.” ([Fly][3])

If you’re building a serverless backend today and your workload is mostly “classic web app” rather than “global high‑volume trading system”, it’s increasingly reasonable to ask:

> “Can I just… use SQLite everywhere?”

Thanks to this new wave of tooling, the answer is often — surprisingly — **yes**.

[1]: https://turso.tech/blog/microsecond-level-sql-query-latency-with-libsql-local-replicas-5e4ae19b628b?utm_source=thinhdanggroup.github.io "Microsecond-level SQL query latency with libSQL local replicas - Turso"
[2]: https://developers.cloudflare.com/d1/?utm_source=thinhdanggroup.github.io "Overview · Cloudflare D1 docs"
[3]: https://fly.io/docs/litefs/?utm_source=thinhdanggroup.github.io "LiteFS - Distributed SQLite · Fly Docs"
[4]: https://github.com/warmchang/libsql-SQLite?utm_source=thinhdanggroup.github.io "GitHub - warmchang/libsql-SQLite: LibSQL is a fork of SQLite that is ..."
[5]: https://www.backova.com/platform/turso?utm_source=thinhdanggroup.github.io "Turso - SQLite for the edge with global replication | Backova"
[6]: https://docs.turso.tech/features/embedded-replicas/introduction?utm_source=thinhdanggroup.github.io "Embedded Replicas - Turso"
[7]: https://blog.canoozie.net/libsql-replication/?utm_source=thinhdanggroup.github.io "LibSQL Replication - blog.canoozie.net"
[8]: https://docs.turso.tech/sdk/ts/quickstart?utm_source=thinhdanggroup.github.io "Turso Quickstart (TypeScript / JS)"
[9]: https://tursodatabase.github.io/libsql-client-ts/index.html?utm_source=thinhdanggroup.github.io "@libsql/client - v0.15.15"
[10]: https://turso.tech/blog/do-it-yourself-database-cdn-with-embedded-replicas?utm_source=thinhdanggroup.github.io "Do It Yourself Database CDN with Embedded Replicas - turso.tech"
[11]: https://developers.cloudflare.com/d1/worker-api/d1-database/ "D1 Database · Cloudflare D1 docs"
[12]: https://workers.cloudflare.com/product/d1?utm_source=thinhdanggroup.github.io "Cloudflare D1 - Serverless SQL Database"
[13]: https://developers.cloudflare.com/d1/best-practices/read-replication/?utm_source=thinhdanggroup.github.io "Global read replication · Cloudflare D1 docs"
[14]: https://blog.cloudflare.com/d1-read-replication-beta/?utm_source=thinhdanggroup.github.io "Sequential consistency without borders: how D1 implements global read ..."
[15]: https://fly.io/docs/litefs/how-it-works/?utm_source=thinhdanggroup.github.io "How LiteFS Works · Fly Docs"
[16]: https://github.com/superfly/litefs/blob/main/docs/ARCHITECTURE.md?utm_source=thinhdanggroup.github.io "litefs/docs/ARCHITECTURE.md at main · superfly/litefs · GitHub"
[17]: https://docs.turso.tech/libsql?utm_source=thinhdanggroup.github.io "libSQL - Turso"
[18]: https://developers.cloudflare.com/d1/worker-api/d1-database/?utm_source=thinhdanggroup.github.io "D1 Database - Cloudflare Docs"
[19]: https://turso.tech/blog/local-first-cloud-connected-sqlite-with-turso-embedded-replicas?utm_source=thinhdanggroup.github.io "Local-First SQLite, Cloud-Connected with Turso Embedded Replicas"
[20]: https://github.com/superfly/litefs/issues/425?utm_source=thinhdanggroup.github.io "Writing to the WAL while using EXCLUSIVE locking mode should be ..."
[21]: https://pypi.org/project/sqlalchemy-cloudflare-d1/?utm_source=thinhdanggroup.github.io "sqlalchemy-cloudflare-d1 · PyPI"
[22]: https://debugg.ai/resources/sqlite-eating-the-cloud-2025-edge-databases-replication-patterns-ditch-server?utm_source=thinhdanggroup.github.io "SQLite Is Eating the Cloud in 2025: Edge Databases, Replication ..."
[23]: https://turso.tech/blog/introducing-embedded-replicas-deploy-turso-anywhere-2085aa0dc242?utm_source=thinhdanggroup.github.io "Introducing Embedded Replicas: Deploy Turso anywhere"
[24]: https://developers.cloudflare.com/d1/get-started/?utm_source=thinhdanggroup.github.io "Getting started · Cloudflare D1 docs"
