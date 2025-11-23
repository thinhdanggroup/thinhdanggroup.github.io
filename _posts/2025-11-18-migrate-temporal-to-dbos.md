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
    overlay_image: /assets/images/migrate-temporal-to-dbos/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/migrate-temporal-to-dbos/banner.png
title: "Migrating from Traditional Workflow Engines (e.g., Temporal) to DBOS: An Engineering Playbook"
tags:
    - dbos
    - temporal
    - migration
---

If you already run Temporal (or a similar workflow engine), you’re not asking “What is durable execution?” anymore.

You’re asking:

-   _Is DBOS just Temporal with a Postgres fetish?_
-   _What does my architecture look like if I switch?_
-   _Can I migrate without detonating production?_

This post is a practical, engineer‑level playbook for moving from an external workflow engine like Temporal to DBOS — with concrete mappings, code, and a staged migration plan.

---

## 1. Where You’re Starting: The Temporal Mental Model

Let’s quickly ground ourselves in the Temporal world you’re probably living in today.

A typical Temporal setup looks like this:

-   **Temporal Service / Cluster** (self‑hosted or Temporal Cloud)

    -   Stores workflow and activity state in a persistence store (Cassandra/MySQL/PostgreSQL).([GitHub][1])
    -   Exposes APIs over gRPC.

-   **Workers**

    -   Host your **workflows** and **activities**.
    -   Poll **task queues** for work.

-   **Clients**

    -   Start workflows, send signals, query workflow state.

Temporal workflows are “workflow-as-code”: deterministic functions that orchestrate activities. All progress is stored as an **event history** in the Temporal service, and workers **replay** that history to resume after crashes.([Temporal Docs][2])

You probably rely on:

-   **Durable timers and long‑running workflows**
-   **Activity retry policies**
-   **Signals, child workflows, and cron schedules**
-   **Temporal Web UI + metrics + visibility store** for debugging and ops([Temporal Docs][2])

This is your baseline.

---

## 2. What Changes with DBOS: From External Orchestrator to Embedded Library

The fundamental shift when you adopt DBOS is architectural:

> **Temporal is an external orchestrator; DBOS is an embedded durable execution library.**([DBOS][3])

### 2.1 DBOS in one paragraph

DBOS Transact (what you actually integrate) is:

-   A **library** you import into your app (TypeScript, Python, Go, Java).([DBOS Docs][4])
-   That stores **workflow state as rows in Postgres** — each workflow’s steps, inputs, and results live in your DB.([Supabase][5])
-   And offers:

    -   **Workflows** (deterministic orchestrators)
    -   **Steps** (arbitrary I/O, non‑deterministic work)
    -   **Transactions** (DB transactions + workflow checkpoint in one commit)([DBOS Docs][6])

You can run it:

-   **Self‑hosted** as part of your service (Node/Python/Go/Java process + Postgres), optionally connected to **DBOS Conductor** for workflow recovery & visualization.([DBOS Docs][7])
-   Or on **DBOS Cloud**, a serverless platform that runs your DBOS app and manages autoscaling, versioning, and recovery.([DBOS Docs][8])

### 2.2 Conceptual contrast

**Temporal**

-   Central service manages workflow histories; workers replay event logs.([Temporal Docs][2])
-   Multi‑language SDKs (Go, Java, TypeScript, Python, .NET, PHP, etc.).([Temporal Docs][9])
-   Persistence options: Cassandra, MySQL, Postgres, SQLite; plus Elasticsearch for advanced visibility.([Temporal Docs][10])

**DBOS**

-   DBOS library runs _inside_ your service; no separate “workflow cluster” to deploy.([DBOS Docs][4])
-   Durable state stored directly in Postgres tables you own.([Supabase][5])
-   First‑class support for TypeScript, Python, Go, Java.([DBOS Docs][4])
-   Built‑in durable queues, scheduled workflows, exactly‑once event processing, and observability via DBOS Console + OpenTelemetry.([DBOS Docs][4])

The big implication:

-   **Temporal**: You architect around “my app talks to Temporal; Temporal coordinates workers.”
-   **DBOS**: You architect around “my app _is_ the durable orchestrator; the DB is the source of truth.”

---

## 3. Temporal → DBOS Mapping Cheat Sheet

Think of this as the Rosetta Stone between your existing Temporal concepts and DBOS.

### 3.1 Core building blocks

| Temporal concept                  | DBOS concept                                                                              | Notes                                               |
| --------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Workflow function                 | Workflow function (`DBOS.workflow()` / `registerWorkflow`)([DBOS Docs][11])               | Both are deterministic orchestrators.               |
| Activity                          | Step (`DBOS.step()` / `runStep`)([DBOS Docs][6])                                          | Anything non‑deterministic (I/O, time, randomness). |
| Activity retry policy             | `StepConfig` (retriesAllowed, maxAttempts, backoffRate, etc.)([DBOS Docs][6])             | Similar semantics, configured at step level.        |
| Task queue                        | DBOS Queue (durable, Postgres‑backed)([DBOS Docs][4])                                     | For fan‑out and concurrency control.                |
| Signal                            | “Communicating with workflows” (DBOS notifications and workflow handles)([DBOS Docs][11]) | Same idea: push messages into a running workflow.   |
| Workflow ID + run ID              | Workflow ID / handle (`DBOS.startWorkflow`, `DBOS.retrieveWorkflow`)([DBOS Docs][11])     | Workflow ID doubles as idempotency key.             |
| Cron schedule / Temporal Schedule | Scheduled workflows + `DBOS.sleep()`([DBOS Docs][11])                                     | DBOS does durable sleep in DB.                      |
| Workflow event history            | Workflow steps + state stored as Postgres rows([DBOS][12])                                | Still fully traceable via DB.                       |

Key difference: **Temporal replays event history through your current code; DBOS replays at the step boundary.** DBOS stores each step’s result, so recovery jumps to “next incomplete step,” not “re-run all user code from the beginning.”

---

## 4. A Concrete Example: Checkout Flow in Temporal vs DBOS

Let’s look at a simplified _checkout_ workflow:

> Reserve inventory → charge card → create order row → send confirmation email.

### 4.1 Temporal version (TypeScript-ish sketch)

**Workflow**

```ts
// src/workflows.ts
import { proxyActivities } from "@temporalio/workflow";
import type * as activities from "./activities";

const {
    reserveInventory,
    chargeCard,
    createOrderRecord,
    sendConfirmationEmail,
} = proxyActivities<typeof activities>({
    taskQueue: "checkout",
    startToCloseTimeout: "1 minute",
});

export async function CheckoutWorkflow(input: CheckoutInput): Promise<string> {
    const reservationId = await reserveInventory(input.items);
    await chargeCard({
        customerId: input.customerId,
        amount: input.total,
        reservationId,
    });
    const orderId = await createOrderRecord({ ...input, reservationId });
    await sendConfirmationEmail({ orderId, email: input.email });
    return orderId;
}
```

**Activities**

```ts
// src/activities.ts
export async function reserveInventory(items: Item[]): Promise<string> {
    // call inventory service / DB here
}

export async function chargeCard(args: ChargeArgs): Promise<void> {
    // call payment gateway
}

export async function createOrderRecord(
    args: CreateOrderArgs
): Promise<string> {
    // write to your DB
}

export async function sendConfirmationEmail(
    args: SendEmailArgs
): Promise<void> {
    // talk to your email service
}
```

You also have a **worker** process that hosts this workflow + activities and polls Temporal for tasks, plus a **client** that starts `CheckoutWorkflow`.([Learn Temporal][13])

### 4.2 DBOS version

With DBOS, there’s no external worker or Temporal service. Your existing backend imports the DBOS library and uses workflows/steps directly.

**Steps and workflow**

```ts
import { DBOS } from "@dbos-inc/dbos-sdk";

export class Checkout {
    @DBOS.step({
        name: "reserveInventory",
        retriesAllowed: true,
        maxAttempts: 5,
    })
    static async reserveInventory(items: Item[]): Promise<string> {
        // call your inventory microservice or DB
    }

    @DBOS.step({ name: "chargeCard", retriesAllowed: true, maxAttempts: 5 })
    static async chargeCard(args: ChargeArgs): Promise<void> {
        // call payment provider
    }

    @DBOS.step({ name: "createOrder" })
    static async createOrder(args: CreateOrderArgs): Promise<string> {
        // usually implemented as a DBOS transaction using your Postgres client
        // inside a datasource transaction. See the Transactions & Datasources docs.:contentReference[oaicite:25]{index=25}
    }

    @DBOS.step({ name: "sendEmail", retriesAllowed: true, maxAttempts: 3 })
    static async sendConfirmationEmail(args: SendEmailArgs): Promise<void> {
        // call your email provider
    }

    @DBOS.workflow()
    static async checkout(input: CheckoutInput): Promise<string> {
        const reservationId = await Checkout.reserveInventory(input.items);

        await Checkout.chargeCard({
            customerId: input.customerId,
            amount: input.total,
            reservationId,
        });

        const orderId = await Checkout.createOrder({
            ...input,
            reservationId,
        });

        await Checkout.sendConfirmationEmail({
            orderId,
            email: input.email,
        });

        return orderId;
    }
}
```

**Starting the workflow in the background**

```ts
// Inside your existing HTTP handler:
app.post("/checkout", async (req, res) => {
    const input: CheckoutInput = req.body;
    const workflowId = `checkout-${input.cartId}`;

    const handle = await DBOS.startWorkflow(Checkout, {
        workflowID: workflowId,
    }) // idempotent start
        .checkout(input);

    // Option 1: wait synchronously
    const orderId = await handle.getResult();

    // Option 2: return immediately and poll / push status later
    res.json({ workflowId, orderId });
});
```

Here:

-   The **DBOS library** runs inside your Node process.
-   All workflow state and step results live in **Postgres**.
-   If the process dies after charging the card but before writing the order row, DBOS resumes the `checkout` workflow at the next step when your app restarts, using the stored step results.([DBOS Docs][11])

---

## 5. Trade‑offs: Why You’d Move (and Why You Might Not)

Migrating from Temporal to DBOS isn’t just a syntax change — it’s an architectural bet. Let’s be honest about the trade‑offs.

### 5.1 Operational model

**DBOS**

-   Adds no extra standalone runtime beyond your app and Postgres.
-   Self‑hosting: you deploy DBOS like any other dependency; DBOS Conductor is a separate control plane for recovery & observability, but it’s not in the request path.([DBOS Docs][7])
-   DBOS Cloud: serverless hosting for your DBOS app + managed Postgres, autoscaling, version management.([DBOS Docs][8])

**Temporal**

-   Requires a Temporal service (self‑hosted cluster linked to Cassandra/MySQL/Postgres) or Temporal Cloud.([Temporal][14])
-   Workers are separate processes that must stay connected and scaled alongside the Temporal service.([Temporal Docs][2])

If your team is already comfortable operating Temporal (or using Temporal Cloud) this is fine. If you’d rather **fold durability into your existing app and DB**, DBOS is compelling.

### 5.2 Stack and ecosystem

-   **Temporal**

    -   More SDKs (Go, Java, TS, Python, .NET, PHP, etc.).([Temporal Docs][9])
    -   Mature ecosystem of tutorials, sample apps, and production deployments.

-   **DBOS**

    -   Focused on TypeScript, Python, Go, Java and Postgres.([DBOS Docs][4])
    -   Tight Postgres centricity is a big win if that’s already your primary DB; a constraint if not.([Supabase][5])

For polyglot microservice fleets with many stacks and databases, Temporal may still be the better “global orchestration backbone.”([Scribbles Into The Void][15])

### 5.3 Self‑hosting complexity

An external comparison (by a Temporal + DBOS user) sums it up:

-   **DBOS**: “single service + Postgres” is relatively simple to self‑host; durability is embedded in your app.([Scribbles Into The Void][15])
-   **Temporal**: multi‑component cluster + DB + visibility store; powerful but more complex to deploy & upgrade.([DeepWiki][16])

### 5.4 Performance & latency

DBOS leans heavily on Postgres to store workflow/step state and emphasizes lower overhead than external orchestrators: you’re usually paying for a couple of SQL operations per step rather than a cross‑service RPC + event log append.([Supabase][5])

Temporal’s architecture is designed for massive scale and throughput, but each step transition involves communication with the Temporal service and persistence in its own store.([Temporal Docs][2])

In practice:

-   For **high‑frequency, low‑latency backend flows** (e.g., web request workflows where you care about tens of milliseconds), an embedded approach like DBOS can be attractive.
-   For **huge numbers of concurrent workflows across many services**, Temporal’s battle‑tested scaling story is a strong argument.

---

## 6. Migration Strategy: A Step‑by‑Step Playbook

Let’s get practical. Here’s a migration plan that doesn’t require a freeze or big‑bang rewrite.

### Phase 0 – Pick Your Landing Zone

Decide how you’ll run DBOS in production:

-   **Option A: Self‑host DBOS + Conductor**

    -   Best if you already self‑host Postgres and want to keep everything inside your infra boundary.([DBOS Docs][7])

-   **Option B: DBOS Cloud**

    -   Best if you want serverless deployment and don’t mind hosted Postgres (or you bring your own Postgres to DBOS Cloud).([DBOS Docs][8])

This choice affects _operations_, but not how you write code.

---

### Phase 1 – Identify Candidate Workflows

You don’t start by porting your most gnarly “all the signals plus child workflows plus patching” monster.

Look for workflows that are:

-   Business‑critical enough to justify effort.
-   Representative of your patterns (timers, retries, external calls).
-   Not so intertwined with weird edge cases that migration becomes archaeology.

Checkout, signup, or “document ingestion” flows are good candidates. DBOS itself uses a document pipeline as a canonical example of migration from Temporal‑style orchestration to embedded workflows.([DBOS][3])

---

### Phase 2 – Map the Workflow’s Concepts

For each Temporal workflow you’re targeting, build a small spreadsheet or doc:

-   **Workflow name + Temporal Workflow ID conventions**
-   **Activities**

    -   External systems they call (Stripe, email, etc.)
    -   Retry policies and timeouts

-   **Signals / queries**
-   **Timers / schedules**
-   **Child workflows or Continue-As-New**
-   **Search attributes and visibility queries**

Then, map them:

1. **Workflow → DBOS workflow**

    Your Temporal `CheckoutWorkflow` becomes `@DBOS.workflow() Checkout.checkout`. The orchestrator logic is usually a near copy‑paste, with activity calls swapped for step or transaction calls.

2. **Activities → DBOS steps / transactions**

    - Idempotent I/O → `@DBOS.step(...)`.
    - DB writes that must be atomic with the workflow checkpoint → DBOS transaction via a datasource.([DBOS Docs][17])

3. **Task queues → DBOS queues**

    If your Temporal workflow fans out thousands of activities over a task queue, you’ll typically map that to a DBOS queue and process using workers attached to it.([DBOS Docs][4])

4. **Signals / queries → workflow handles + communication APIs**

    DBOS exposes workflow handles (`DBOS.startWorkflow` returns a handle, `DBOS.retrieveWorkflow` gets one by ID) and APIs for communicating with workflows. That’s where you recreate “signal a running workflow” semantics.([DBOS Docs][11])

5. **Schedules / cron → DBOS sleep/scheduled workflows**

    Temporal cron or Schedules map to:

    - long sleeps via `DBOS.sleep()`, or
    - DBOS’s scheduled workflows feature, which runs workflows exactly‑once per interval.([DBOS Docs][11])

6. **Search attributes → Postgres queries**

    Anything you used to store as custom search attributes can become normal columns in your DBOS system tables or your own application tables, queried with SQL.([DBOS][12])

---

### Phase 3 – Port the Code (Incrementally)

Here’s a pragmatic approach:

1. **Introduce DBOS into your existing service**

    - Add the DBOS library.
    - Configure it to point at:

        - A **system database** (holds workflow/queue state).
        - Optionally, an **application database** for transactions.([DBOS Docs][18])

    - Leave the Temporal code untouched for now.

2. **Re‑implement the target workflow in DBOS**

    - Lift the **orchestration logic** from your Temporal workflow function into a DBOS workflow.
    - Refactor each Temporal activity into a DBOS step or transaction class method.
    - Copy retry policies to `StepConfig` (maxAttempts, intervalSeconds, backoffRate, etc.).([DBOS Docs][6])
    - Ensure deterministic code remains only in the workflow; all I/O moves to steps/transactions (similar to Temporal’s own deterministic constraints).([Temporal Docs][2])

3. **Wrap DBOS calls in a feature flag**

    For the call site (e.g., an HTTP handler), add a toggle:

    ```ts
    if (useDbosCheckout) {
        const handle = await DBOS.startWorkflow(Checkout, {
            workflowID,
        }).checkout(input);
        // ...
    } else {
        await temporalClient.workflow.start(CheckoutWorkflow, {
            /* ... */
        });
    }
    ```

    At this point, still send real production traffic only to Temporal.

---

### Phase 4 – Shadow / “Dark” Runs

Before flipping traffic, run DBOS side‑by‑side as a **shadow**:

-   For every Temporal workflow start:

    -   Generate a unique business key (e.g. `checkout-${orderId}`).
    -   Start the DBOS workflow with that ID as well, but have its steps call stubbed or idempotent endpoints:

        -   Either use feature flags inside steps to _not_ make real side‑effecting calls (just log).
        -   Or route DBOS’s calls to a sandbox environment of your downstreams.

Then:

-   Compare outcomes (e.g. DBOS’s computed order total vs what Temporal’s path produced).
-   Use DBOS’s web UI and traces to verify step ordering and retry behavior match expectations.([Hacker News][19])

Think of this as a canary — you’re validating behavior and performance without risking double‑charges or duplicate emails.

---

### Phase 5 – Flip New Traffic

Once you’re confident:

1. **Make DBOS the source of truth for new executions**

    - New checkouts are started only as DBOS workflows.
    - You stop creating new Temporal workflows for that use case.

2. **Let old Temporal workflows drain**

    - Keep your Temporal cluster/Cloud namespace up.
    - Wait until all relevant workflows are completed or cancelled.
    - If you have very long‑lived workflows, consider:

        - Leaving them on Temporal indefinitely, or
        - Designing explicit “handoff points” where you finish the Temporal workflow and start a DBOS one using the same business keys.

3. **Switch dashboards and alerts**

    - Migrate your alerts and logs from Temporal’s metrics to DBOS metrics/OTel traces and Console.([Hacker News][19])

Rinse and repeat for other workflows.

---

## 7. Handling Real‑World Gotchas

### 7.1 In‑flight workflows

**Hard truth:** there’s no generic, safe way to “move” an in‑flight Temporal workflow execution into DBOS.

Common pragmatic strategy:

-   Let existing Temporal workflows complete where they are.
-   Use DBOS for all _new_ requests.
-   If you must migrate partially completed long‑running business processes, treat it as a **domain‑level state migration**, not a “copy the workflow internals” problem:

    -   Add a new DBOS workflow that starts from an intermediate business state (“card already charged, order not shipped”).
    -   Explicitly guard against replaying side effects.

### 7.2 Idempotency & workflow IDs

Temporal uses `(namespace, workflowId, runId)` to uniquely identify executions. DBOS uses a single workflow ID per execution, and if you reuse an ID, it acts as an **idempotency key** — only the first run “wins.”([Temporal Docs][2])

Migration best practices:

-   If you previously used something like `order-${orderId}` as the Temporal workflow ID, reuse exactly that as the DBOS workflow ID.
-   Make DBOS workflow IDs the _business idempotency key_ across your system. If upstream services retry, they should re‑send the same workflow ID so DBOS doesn’t re‑execute the flow.

### 7.3 Timers, sleeps, and cron

Temporal offers durable timers and schedules.([Temporal Docs][2])

In DBOS:

-   Use `DBOS.sleep()` for “wake me up in N minutes/hours/days.” It stores wakeup time in Postgres so the workflow can restart through process crashes and still wake up on schedule.([DBOS Docs][11])
-   Use DBOS’s scheduled workflows or external trigger receivers for cron‑like jobs (e.g., nightly reconciliation).([DBOS Docs][20])

When migrating, make sure you:

-   Match cadence and jitter.
-   Translate any Temporal cron expression to the equivalent DBOS schedule configuration (you may choose to keep some ultra‑simple cron outside DBOS entirely).

### 7.4 Observability and debugging

Temporal gives you:

-   Detailed event histories per workflow.
-   Web UI and advanced visibility queries.([Temporal Docs][2])

DBOS gives you:

-   A web console showing workflows, steps, queues, and status.
-   OpenTelemetry traces emitted for each workflow/step, which can be sent to your existing observability stack.([Hacker News][19])
-   Time‑travel style debugging (in DBOS Cloud), letting you inspect state at each step.([DBOS Docs][8])

Migration task list:

-   Replicate key dashboards (latency per step, failure rates, queue depth).
-   Ensure alerting adapts from “Temporal workflows stuck in state X” to “DBOS workflows / queues lagging or failing step Y.”

### 7.5 Versioning and safe rollouts

Temporal has **patching** and versioning APIs to manage deterministic workflow changes over time.([GitHub][21])

DBOS’s approach:

-   Each workflow execution is tagged with the **code version** that ran it; self‑hosted DBOS typically recovers workflows only on executors running the same code version.([DBOS Docs][11])
-   DBOS Cloud automates version management: old workflows continue on old code; new workflows start on new code.([DBOS Docs][22])
-   You can **fork** workflows from a specific step to rerun them under a different code version.([DBOS Docs][23])

Practically:

-   In self‑hosted environments, roll out new versions the same way you’d roll a database migration:

    -   Keep old workers around for old workflows until they drain.
    -   Or explicitly use DBOS’s forking tools when you want to rerun under new code.

---

## 8. Summary: When DBOS Makes Sense for a Temporal Shop

If you’re already bought into Temporal, you’ve invested in a powerful model. So when does DBOS actually justify a migration?

Patterns where DBOS shines:

-   Your core backend is already **heavily Postgres‑centric** and you’d like orchestration + state + reliability to live in the same place.([DBOS][12])
-   You want **lighter infrastructure**: just your app + Postgres + (optionally) DBOS Cloud/Conductor, rather than a separate workflow cluster.
-   Your workflows are mostly within **one or a few services**, in languages DBOS supports today (TS, Python, Go, Java).
-   You care deeply about **latency** and want durable execution without the extra network hop to an external orchestrator.

Patterns where sticking with Temporal (or using both) is reasonable:

-   Large, **polyglot microservice** architectures requiring cross‑language workflows and a shared orchestration backbone.([Scribbles Into The Void][15])
-   Heavy use of Temporal’s advanced features (complex child workflow trees, Nexus, multi‑region Temporal Cloud setups) where DBOS equivalents aren’t yet a drop‑in.
-   Existing deep operational investment in Temporal, including custom tooling around its event histories and visibility.

The key is: you don’t have to choose **forever** or **everywhere**.

You can:

-   Keep Temporal for cross‑service, polyglot orchestration.
-   Adopt DBOS inside individual services where the “embedded workflow + Postgres rows” model gives you lower latency and simpler ops.
-   Gradually migrate high‑value workflows from Temporal to DBOS using the phased approach above.

---

## 9. Further Reading

If you want to dig deeper after this:

-   **DBOS**

    -   Welcome to DBOS (docs) – what DBOS is and its features.([DBOS Docs][4])
    -   “Benchmarking External and Embedded Durable Workflows” – DBOS’s own Temporal vs DBOS comparison with code.([DBOS][3])
    -   TypeScript workflow & step tutorials – details on `@DBOS.workflow`, `@DBOS.step`, retries, queues, and sleep.([DBOS Docs][6])

-   **Temporal**

    -   TypeScript SDK dev guide – deep dive into workflows, activities, retries, timers, and versioning.([Temporal Docs][9])
    -   Temporal Workflow Execution Overview – conceptual explanation of event histories and replay.([Temporal Docs][2])

-   **Comparisons & context**

    -   “Making Apps Durable with 10x Less Code” (DBOS) – a detailed architectural comparison with Temporal.([DBOS][3])
    -   “DBOS vs. Temporal – Choosing Your Durable Executor” – neutral trade‑off analysis, especially for on‑prem deployments.([Scribbles Into The Void][15])
    -   DBOS origin story and research on database‑oriented operating systems.([Wikipedia][24])

If you’d like, next we can zoom into one specific angle – for example, _“Exactly‑once event processing: Temporal vs DBOS”_ or _“Designing your Postgres schema for DBOS workflows”_ – and unpack that in detail.

[1]: https://github.com/temporalio/temporal "GitHub - temporalio/temporal: Temporal service"
[2]: https://docs.temporal.io/workflow-execution "Temporal Workflow Execution Overview | Temporal Platform Documentation"
[3]: https://www.dbos.dev/blog/durable-execution-coding-comparison "Making Apps Durable with 10x Less Code | DBOS"
[4]: https://docs.dbos.dev/ "Welcome to DBOS! | DBOS Docs"
[5]: https://supabase.com/blog/durable-workflows-in-postgres-dbos?utm_source=thinhdanggroup.github.io "Running Durable Workflows in Postgres using DBOS"
[6]: https://docs.dbos.dev/typescript/tutorials/step-tutorial "Steps | DBOS Docs"
[7]: https://docs.dbos.dev/production/self-hosting/conductor "DBOS Conductor | DBOS Docs"
[8]: https://docs.dbos.dev/production/dbos-cloud/deploying-to-cloud?utm_source=thinhdanggroup.github.io "Deploying to DBOS Cloud | DBOS Docs"
[9]: https://docs.temporal.io/develop/typescript?utm_source=thinhdanggroup.github.io "TypeScript SDK developer guide | Temporal Platform Documentation"
[10]: https://docs.temporal.io/temporal-service/persistence?utm_source=thinhdanggroup.github.io "Persistence | Temporal Platform Documentation"
[11]: https://docs.dbos.dev/typescript/tutorials/workflow-tutorial "Workflows | DBOS Docs"
[12]: https://www.dbos.dev/blog/why-workflows-should-be-postgres-rows?utm_source=thinhdanggroup.github.io "Why All Your Workflows Should Be Postgres Rows | DBOS"
[13]: https://learn.temporal.io/getting_started/typescript/hello_world_in_typescript/ "Build a Temporal Application from scratch in TypeScript | Learn Temporal"
[14]: https://temporal.io/how-it-works?utm_source=thinhdanggroup.github.io "How the Temporal Platform Works"
[15]: https://void.abn.is/dbos-vs-temporal-choosing-your-durable-executor/ "DBOS vs. Temporal - Choosing Your Durable Executor"
[16]: https://deepwiki.com/temporalio/temporal/8.4-database-schema-management?utm_source=thinhdanggroup.github.io "Database Schema Management | temporalio/temporal | DeepWiki"
[17]: https://docs.dbos.dev/typescript/tutorials/transaction-tutorial?utm_source=thinhdanggroup.github.io "Transactions & Datasources | DBOS Docs"
[18]: https://docs.dbos.dev/typescript/programming-guide?utm_source=thinhdanggroup.github.io "Learn DBOS TypeScript | DBOS Docs"
[19]: https://news.ycombinator.com/item?id=42379974&utm_source=thinhdanggroup.github.io "Running Durable Workflows in Postgres Using DBOS | Hacker News"
[20]: https://docs.dbos.dev/typescript/tutorials/workflow-management?utm_source=thinhdanggroup.github.io "Workflow Management | DBOS Docs"
[21]: https://github.com/temporalio/samples-typescript/blob/main/README.md?utm_source=thinhdanggroup.github.io "samples-typescript/README.md at main - GitHub"
[22]: https://docs.dbos.dev/architecture?utm_source=thinhdanggroup.github.io "DBOS Architecture | DBOS Docs"
[23]: https://docs.dbos.dev/production/dbos-cloud/workflow-management?utm_source=thinhdanggroup.github.io "Workflow Management | DBOS Docs"
[24]: https://en.wikipedia.org/wiki/DBOS?utm_source=thinhdanggroup.github.io "DBOS"
