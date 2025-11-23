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
    overlay_image: /assets/images/temporal-reliable-ai-pipeline/banner.png
    overlay_filter: 0.5
    teaser: /assets/images/temporal-reliable-ai-pipeline/banner.png
title: "Untitled Blog Post"
tags:
    - temporal
    - ai pipeline
    - agent
---

There’s a decent chance you have a cron job somewhere that looks like this:

```bash
0 3 * * * /usr/local/bin/run_ai_pipeline.sh >> /var/log/ai.log 2>&1
```

It worked fine when “AI pipeline” meant “run one script that calls an API and uploads a file.”

But now that pipeline is a small universe:

-   Fetch data from a dozen sources
-   Chunk and embed documents
-   Fan out queries to an LLM (with rate limits and timeouts)
-   Call tools, write results to databases, send notifications
-   Maybe involve a human who approves or edits output

…and somewhere around step 7, the network flakes, your container restarts, or OpenAI returns a 500.

Cron has no idea.

It doesn’t know which step you were on. It doesn’t know what already succeeded. It doesn’t know that you just re-ran the same expensive LLM call three times.

As AI workloads get more complex, that “best effort” model stops being cute and starts burning money, time, and trust. This is exactly the gap Temporal’s **Durable Execution** model is built to fill ([temporal.io][1])—and why it’s quietly becoming the runtime backbone for LLM pipelines and agent orchestration.

This post is about going _beyond cron_: what durable execution really is, how Temporal works under the hood, and how it changes the way you design AI systems.

---

## 1. Cron is great… until you add LLMs

Cron is beautifully dumb.

It answers exactly one question: **“When should I run this command?”** Everything else—state, errors, retries, partial progress, rate limits—is your problem.

A lot of AI architectures today still look like this:

1. Cron fires a script.
2. Script pulls “jobs” from a queue.
3. For each job:

    - Call an LLM.
    - Call some tools.
    - Save stuff in a DB.

4. Hope nothing explodes mid-way.

Here’s what goes wrong once LLMs enter the picture:

-   **LLM calls are expensive** — If you crash after 20 minutes of multi-step reasoning, you don’t want to “just start over.”
-   **Pipelines are multi-step and stateful** — You can’t just say “this job failed”; you need to know which steps completed.
-   **Failures are normal, not exceptional** — Rate limiting, flaky APIs, transient DB issues. You need retries with _semantics_, not a `for` loop with `sleep(5)`.
-   **Pipelines can run for hours or days** — Waiting for a human-in-the-loop, backfills over millions of documents, long research tasks.
-   **Agents are loops, not DAGs** — An agent might decide its next tool at runtime. That’s not a simple “run step 3 after step 2” anymore.

You _can_ try to solve all of this with hand-rolled state machines, idempotency keys, and scattered checkpointing. Many teams do. And then they slowly reinvent a workflow engine.

Temporal’s pitch is basically: _let’s give you that engine as a programming model_, instead of as a tangle of queues and custom glue. ([temporal.io][1])

---

## 2. Durable Execution in one sentence

Let’s define the core idea:

> **Durable Execution** means your function can outlive the process that runs it—_and still behave as if it ran once, in one place, without losing its mind._

Temporal’s docs describe a Workflow Execution as a “durable, reliable, and scalable function execution,” and treat it as the main unit of execution in an application. ([Temporal][2])

What does that really mean?

Normally, when you call a function:

-   Its local variables live on a stack in memory.
-   If the process crashes, _poof_—that stack is gone.
-   To recover, you need external state: DB rows, logs, maybe manual intervention.

With durable execution:

-   The runtime records a **history of events**: “Timer started”, “Activity completed with result X”, “Signal received with payload Y.” ([Temporal][3])
-   Your workflow function is written so its behavior is **fully determined by that history**.
-   On failure, Temporal replays the history into your workflow code, re-creating its state (locals, progress) and continuing as if nothing happened.

Think of it like a game that stores not just a saved screenshot, but every input you ever pressed. Replaying the inputs recreates the exact game state.

This is crucial for AI pipelines:

-   The decision _“Do we need another research iteration?”_ is part of the workflow’s logic and is replayable.
-   The actual LLM call is a side effect whose **result** is recorded in history and never re-executed on replay.

---

## 3. Temporal in three moving parts

Temporal gives you durable execution as a service. Conceptually, it has three roles:

1. **Temporal Service (cluster)**

    - Stores workflow histories durably.
    - Generates tasks (e.g., “run this workflow code”, “run this activity”).
    - Manages timers, retries, and task queues. ([temporal.io][1])

2. **Workers (your code)**

    - Regular processes you run (Docker, Kubernetes, whatever).
    - Host your **Workflows** (orchestration logic) and **Activities** (side-effecting work).
    - Poll Temporal for tasks and push results back. ([Temporal][4])

3. **Clients (also your code)**

    - Start workflows, send signals, query status, etc. ([Temporal][4])

The key abstraction is:

-   **Workflows** = deterministic orchestration logic (no direct HTTP calls, no random `Date.now()`).
-   **Activities** = anything that can fail or be non-deterministic: HTTP calls, DB writes, LLM calls. ([Temporal][5])

When a workflow schedules an activity (“run this LLM call”), Temporal:

1. Writes an event “Activity A scheduled” into history.
2. Enqueues an activity task to a **Task Queue**.
3. Some worker picks it up, runs your activity code (e.g., an OpenAI call), and returns the result.
4. Temporal writes “Activity A completed with result R” into history.

If the worker dies halfway through?

-   Temporal will deliver the activity task to another worker (with retries governed by your policy).
-   If the Temporal cluster itself restarts, history is persisted in its backing store. ([Temporal Assets][6])

From your workflow’s point of view, you `await` an activity and either get a result or a failure—no manual polling, no custom retry code.

---

## 4. Deterministic workflows vs stochastic models

At first glance, this sounds incompatible with LLMs.

LLMs are stochastic: you call them twice with the same prompt and parameters, and you might get different text. That’s basically the opposite of determinism.

Temporal solves this tension by drawing a hard line:

-   **Workflows must be deterministic.**
-   **Activities are allowed to be non-deterministic; their _results_ are recorded.** ([Temporal][5])

On the first run:

-   Your workflow calls an activity like `runLLMAnalysis(prompt)`.
-   The activity hits the OpenAI API and returns a string.
-   Temporal stores that output in workflow history.

On replay:

-   The workflow _does not_ call the API again.
-   Temporal “replays” the history, feeding the recorded output back into the workflow at the same point.

So as long as your workflow logic only uses:

-   Its input arguments,
-   Recorded activity results,
-   Deterministic APIs provided by the Temporal SDK (e.g., workflow-specific `now()`, `sleep()`),

…it will follow the exact same control flow on replay. ([Temporal][3])

Meanwhile, your LLMs stay non-deterministic—but only on the _first_ execution of each step.

This gives you a nice mental rule:

> **Workflows own decisions. Activities own side effects.**

For AI pipelines, that means:

-   The workflow decides _when_ to call the model, _which_ tools to use, and _when_ to stop iterating.
-   Each LLM call is a durable step whose result is saved, so a deploy or crash doesn’t silently redo work.

---

## 5. A durable AI pipeline in Temporal (TypeScript example)

Let’s build a simplified Temporal-powered AI pipeline in TypeScript:

**Goal:** Given a `jobId`, run a research pipeline:

1. Fetch documents.
2. Generate embeddings and store them.
3. Ask an LLM to produce an analysis.
4. Store the final result.

We’ll show:

-   Activities that talk to the outside world (HTTP, DB, LLMs).
-   A workflow that orchestrates these activities reliably.

### 5.1. Activities: all the messy parts

```ts
// src/activities.ts
// These run in a normal Node.js context.

export interface SourceDoc {
    id: string;
    content: string;
}

export interface EmbeddingResult {
    docId: string;
    vector: number[];
}

export interface AnalysisResult {
    jobId: string;
    summary: string;
    reasoning: string;
}

export async function fetchDocuments(jobId: string): Promise<SourceDoc[]> {
    // Call your own APIs/DBs/cloud storage here.
    // Any network failure will be retried according to Activity retry policy.
    console.log(`[activities] Fetching docs for job ${jobId}`);
    // Placeholder: in real life you'd pull from S3, Postgres, etc.
    return [
        { id: "doc-1", content: "First document text..." },
        { id: "doc-2", content: "Second document text..." },
    ];
}

export async function embedDocuments(
    docs: SourceDoc[]
): Promise<EmbeddingResult[]> {
    console.log(`[activities] Embedding ${docs.length} docs`);
    // You might batch into your vector DB here, or call an embeddings API.
    // This is intentionally non-deterministic (remote API call).
    return docs.map((d) => ({
        docId: d.id,
        vector: [Math.random(), Math.random(), Math.random()], // placeholder!
    }));
}

export async function runLLMAnalysis(
    jobId: string,
    docs: SourceDoc[]
): Promise<AnalysisResult> {
    console.log(`[activities] Running LLM analysis for job ${jobId}`);
    // Call your favorite LLM here.
    // For example, using OpenAI's SDK (pseudo-code):
    //
    // const response = await openai.chat.completions.create({
    //   model: 'gpt-4.1',
    //   messages: [...],
    // });
    //
    // return { ...based on response... };

    return {
        jobId,
        summary: "Fake summary from LLM.",
        reasoning: "Fake chain-of-thought or tool usage (not shown to users).",
    };
}

export async function storeResults(result: AnalysisResult): Promise<void> {
    console.log(`[activities] Storing result for job ${result.jobId}`);
    // Write to DB, send notifications, etc.
}
```

### 5.2. Workflow: the reliable conductor

Temporal workflows run in a special isolated environment for determinism; you can’t just `import` the OpenAI SDK and start calling it. Instead, you **proxy** activities and orchestrate them:

```ts
// src/workflows.ts
import { proxyActivities } from "@temporalio/workflow";
import type * as activities from "./activities";

export interface PipelineInput {
    jobId: string;
}

export interface PipelineOutput {
    jobId: string;
    docCount: number;
}

const { fetchDocuments, embedDocuments, runLLMAnalysis, storeResults } =
    proxyActivities<typeof activities>({
        startToCloseTimeout: "10 minutes",
        retry: {
            maximumAttempts: 5,
            backoffCoefficient: 2.0,
        },
    });

export async function aiPipelineWorkflow(
    input: PipelineInput
): Promise<PipelineOutput> {
    const { jobId } = input;

    // Step 1: Fetch documents (Activity).
    const docs = await fetchDocuments(jobId);

    // Step 2: Embed them (Activity; might call vector DB).
    const embeddings = await embedDocuments(docs);
    // You might store embeddings inside embedDocuments, or in another Activity.

    // Step 3: Run LLM analysis (Activity).
    const analysis = await runLLMAnalysis(jobId, docs);

    // Step 4: Store final results (Activity).
    await storeResults(analysis);

    // Step 5: Return minimal workflow result.
    return {
        jobId,
        docCount: docs.length,
    };
}
```

There are a few big wins hiding in this simple code:

-   If the process running this workflow crashes after `embedDocuments` succeeds but before `storeResults`, Temporal will replay history, re-create the workflow’s state, and continue from the `await storeResults(...)` line.
-   The LLM call happens once; its output is part of the history. On replay, no extra tokens are burned.
-   Retries, timeouts, and backoff are declarative in the workflow when you create the activity proxies.

### 5.3. Worker: connecting your code to Temporal

Finally, a worker binds workflows and activities to a task queue:

```ts
// src/worker.ts
import { Worker } from "@temporalio/worker";
import * as workflowModule from "./workflows";
import * as activities from "./activities";

async function run() {
    const worker = await Worker.create({
        // Temporal uses this to load your workflow code in an isolated runtime.
        workflowsPath: require.resolve("./workflows"),
        activities,
        taskQueue: "ai-pipeline", // name used by clients to start workflows
    });

    await worker.run(); // blocks until process is stopped
}

run().catch((err) => {
    console.error(err);
    process.exit(1);
});
```

Temporal’s TypeScript docs and tutorials walk through this full setup in detail—creating a project, running a dev server with `temporal server start-dev`, and starting workers connected to a task queue. ([Learn Temporal][7])

---

## 6. Why durable execution is such a good fit for AI pipelines

AI pipelines are _textbook_ use cases for durable workflows. If you list out the pain points, Temporal maps to them almost directly:

### 6.1. Expensive steps

LLM calls, vector indexing, and large data movement are costly. You want:

-   **At-most-once semantics for external side effects** (as seen by your business logic).
-   The ability to retry failed steps without losing already-completed work.

Temporal achieves this by:

-   Treating activities as individually retriable steps with configurable retry policies.
-   Persisting activity results so they’re not recomputed on replay. ([Temporal Assets][6])

### 6.2. Long-running jobs

It’s perfectly normal for:

-   An agent to work for hours.
-   A data backfill to run for days.
-   A workflow to wait for a human approval for weeks.

In Temporal, timers and sleep calls are **server-side**, not process-local:

-   `workflow.sleep('3 days')` stores a timer in Temporal’s backend, not in memory.
-   Your workers can restart, deploy, scale horizontally—all without losing this “sleep.” ([Temporal Assets][6])

### 6.3. Human-in-the-loop and tools

AI apps often need:

-   “Ask a user to confirm this action.”
-   “Wait for a human editor to approve the draft.”
-   “Call tool X, then Y, unless user cancels.”

Temporal’s Signals/Queries and event history model fit this nicely:

-   A workflow can sleep indefinitely waiting for a signal (e.g., “user_approved”).
-   When the signal arrives, it becomes an event in history and the workflow resumes. ([Temporal][5])

### 6.4. Observability and debugging

Debugging an agent that calls multiple tools and models is… not fun.

Temporal gives you:

-   A full event history: which activities ran, their inputs, outputs, retries. ([Temporal][3])
-   A Web UI where you can see workflow status, task queues, and timing.
-   The ability to replay workflows locally for debugging.

Instead of diffing random log lines, you can inspect a structured timeline of your AI pipeline.

### 6.5. Evolution and versioning

AI stacks evolve constantly:

-   You change the system prompt.
-   You add a new step to the pipeline.
-   You swap one model for another.

Temporal has explicit guidance and features for **workflow versioning**—rolling out new behavior while allowing old workflows to finish with their original logic. ([Temporal][5])

That’s much saner than trying to keep a pile of “v2”, “v3”, “v3_final” scripts straight in cron.

---

## 7. Agents, loops, and unknown control flow

Cron is fundamentally about _known_ schedules. Traditional DAG orchestrators (Airflow, etc.) are about _known_ graphs.

But AI agents often look more like this:

```ts
while (!goalReached) {
    const plan = await llm.plan(currentState);
    const toolResult = await runTool(plan.nextAction);
    currentState = await llm.summarize({ currentState, toolResult });
}
```

The number of loop iterations is unknown ahead of time. The sequence of tools is decided at runtime.

Temporal is surprisingly good at this, because workflows are just code:

-   You can implement loops, dynamic branches, and recursion directly.
-   Each loop iteration can:

    -   Call one or more LLMs (as activities),
    -   Call tools,
    -   Decide what to do next based on the _recorded_ results.

Temporal and the broader ecosystem have started leaning into this pattern:

-   Temporal’s own blog discusses how “AI apps and agents are distributed systems on steroids,” and why durable execution is a perfect fit for them. ([temporal.io][8])
-   Integrations with frameworks like the OpenAI Agents SDK and Pydantic AI wrap agents with Temporal workflows so they can survive failures, restarts, and long-running interactions. ([temporal.io][9])

From a mental-model standpoint:

> **Agents choose the next step; Temporal guarantees each step actually happens (once) and is remembered.**

---

## 8. Beyond Cron: how the mental model changes

Let’s contrast how you think about an AI pipeline with Cron/queues vs Temporal.

| Concern                       | Cron + scripts/queues                                | Temporal Durable Workflows                           |
| ----------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| Scheduling                    | OS-level cron, stateless                             | Temporal Schedules / external triggers               |
| Progress tracking             | Ad-hoc DB flags, logs                                | Workflow event history                               |
| Retries                       | Hand-written loops, backoff, idempotency everywhere  | Declarative retry policies per Activity              |
| Long-running waits            | `sleep` in process, hacked heartbeats                | Server-side timers, `workflow.sleep`                 |
| Crashes & deploys             | You restart jobs manually or accept partial failures | Workflows resume from last persisted event           |
| Observability                 | Grep logs                                            | Web UI, history, replay                              |
| Non-deterministic work (LLMs) | Called wherever; risk of duplicate calls             | Isolated in Activities with durable results          |
| Agents / dynamic loops        | Custom state machine code                            | Native control flow in workflows + durable execution |

Cron doesn’t become useless—you might still use it to kick off a new workflow every night for a reporting job—but it’s no longer the source of truth for your system’s behavior.

Instead, you design your AI system as a set of **long-lived, reliable functions** (workflows) that orchestrate side-effecting operations (activities).

---

## 9. Getting started: a practical path

If this is all new, it can sound like a huge rewrite. It doesn’t have to be.

Here’s a pragmatic on-ramp:

1. **Run Temporal locally**

    - Install the CLI and start a dev server (one command: `temporal server start-dev`). ([Learn Temporal][7])

2. **Wrap one part of your pipeline**

    - Pick a reliability-critical job (e.g., “process nightly docs”).
    - Turn its orchestration into a Temporal workflow.
    - Keep your existing code as activities—HTTP calls, DB writes, LLM calls, etc.

3. **Use Temporal as your “AI cron”**

    - Either:

        - Keep your old cron, but have it start a Temporal workflow instead of running the whole pipeline, or
        - Use Temporal’s native schedules/cron support to trigger workflows on a cadence.

4. **Lean into workflow semantics**

    - Gradually move more logic into workflows:

        - Human approvals via signals.
        - Complex retry policies.
        - Sub-workflows for per-document processing.

5. **Try an agent pattern**

    - Take a simple agent loop and adapt it into a workflow: the planning and decision logic stays in the workflow, while model/tool calls are activities.
    - Or experiment with an existing integration (e.g., Temporal + OpenAI Agents or Pydantic AI). ([temporal.io][9])

Within a couple of iterations, you’ll notice a shift: you’re no longer asking “Did the cron job run?” but “What’s the state of that workflow?”—and Temporal can answer that precisely, even if your infrastructure has been restarted a dozen times in between.

---

## 10. Key takeaways & further reading

Let’s recap the big ideas:

-   **Cron is about time, not correctness.** It’s fine for simple tasks, but it has no concept of partial progress, retries, or long-running stateful workflows.

-   **Durable Execution turns “a function call” into “a durable, replayable execution”** that can survive crashes, deploys, and network failures while behaving as if it ran once, in one place. ([Temporal][2])

-   **Temporal gives you durable execution as a programming model**, with:

    -   Deterministic workflows for orchestration,
    -   Activities for side effects and non-deterministic operations,
    -   Event histories, retries, and timers built in. ([Temporal][5])

-   **AI pipelines and agents map almost perfectly onto workflows**, because they are:

    -   Multi-step, long-running, and failure-prone,
    -   Expensive to recompute,
    -   Often interactive and tool-driven. ([temporal.io][8])

-   **You don’t have to rewrite everything at once.** Start by wrapping your existing pipeline in a single workflow and grow from there.

If you want to go deeper, good next reads include:

-   Temporal docs on **Workflows, Activities, and event history** for a deeper look at determinism and replay. ([Temporal][5])
-   Temporal’s “Durable Execution meets AI” and “Durable AI agent” resources for AI-specific patterns and examples. ([temporal.io][8])
-   The TypeScript SDK tutorials if you’re a Node/TypeScript shop and want to get hands-on quickly. ([Learn Temporal][7])

The punchline: as AI systems evolve from “one-off API call” to “always-on, multi-step, agentic workflows,” the old cron-plus-scripts architecture creaks under the weight.

Temporal’s durable execution model gives you something closer to a **language runtime for workflows**—one where time, failures, and long-lived state are first-class concerns. For reliable AI in production, that’s starting to look less like an option and more like table stakes.

[1]: https://temporal.io/?utm_source=thinhdanggroup.github.io "Durable Execution Solutions | Temporal"
[2]: https://docs.temporal.io/workflow-execution?utm_source=thinhdanggroup.github.io "Temporal Workflow Execution Overview"
[3]: https://docs.temporal.io/encyclopedia/event-history/event-history-typescript?utm_source=thinhdanggroup.github.io "Event History Walkthrough with the TypeScript SDK | Temporal Platform ..."
[4]: https://docs.temporal.io/develop/typescript/core-application?utm_source=thinhdanggroup.github.io "Core application - TypeScript SDK - Temporal"
[5]: https://docs.temporal.io/workflows?utm_source=thinhdanggroup.github.io "Temporal Workflow | Temporal Platform Documentation"
[6]: https://assets.temporal.io/durable-execution.pdf?utm_source=thinhdanggroup.github.io "Building Reliable Applications with Durable Execution - Temporal"
[7]: https://learn.temporal.io/getting_started/typescript/hello_world_in_typescript/?utm_source=thinhdanggroup.github.io "Build a Temporal Application from scratch in TypeScript"
[8]: https://temporal.io/blog/durable-execution-meets-ai-why-temporal-is-the-perfect-foundation-for-ai?utm_source=thinhdanggroup.github.io "Durable Execution meets AI: Why Temporal is ideal for AI agents ..."
[9]: https://temporal.io/blog/announcing-openai-agents-sdk-integration?utm_source=thinhdanggroup.github.io "Production-ready agents with the OpenAI Agents SDK + Temporal"
